from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

app = FastAPI()

# Ulangan foydalanuvchilar: { username: WebSocket }
active_connections: Dict[str, WebSocket] = {}

# Xabarlar tarixi: Barcha xabarlar shu yerda saqlanadi
message_history: List[dict] = []

# AI botning doimiy nomi
AI_BOT_NAME = "AI_Assistant"

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    print(f"[+] {username} ulandi!")
    
    # 1. Ulangan zahoti foydalanuvchiga mavjud xabarlar tarixini yuboramiz
    await send_chat_history(websocket)
    
    # 2. Foydalanuvchilar ro'yxatini yangilab hammaga yuboramiz
    await broadcast_user_list()

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[{username} dan xabar]: {data}")
            message_data = json.loads(data)
            receiver = message_data.get("receiver")
            text = message_data.get("text")
            
            if not receiver or not text:
                continue

            # Xabarni tarixga qo'shamiz
            msg_item = {"sender": username, "receiver": receiver, "text": text}
            message_history.append(msg_item)

            # Agar xabar AI botga yuborilgan bo'lsa
            if receiver == AI_BOT_NAME:
                ai_response_text = f"Salom {username}! Sizning xabaringiz qabul qilindi: '{text}'. Men sizning AI yordamchingizman!"
                
                ai_msg_item = {"sender": AI_BOT_NAME, "receiver": username, "text": ai_response_text}
                message_history.append(ai_msg_item)

                # Foydalanuvchiga AI javobini yuboramiz
                payload = json.dumps({
                    "sender": AI_BOT_NAME,
                    "text": ai_response_text
                })
                await websocket.send_text(payload)

            elif receiver in active_connections:
                # Oddiy foydalanuvchiga yuborish
                receiver_socket = active_connections[receiver]
                payload = json.dumps({
                    "sender": username,
                    "text": text
                })
                await receiver_socket.send_text(payload)
                
    except WebSocketDisconnect:
        if username in active_connections:
            del active_connections[username]
        print(f"[-] {username} uzildi!")
        await broadcast_user_list()

async def send_chat_history(websocket: WebSocket):
    history_payload = json.dumps({
        "type": "history_sync",
        "messages": message_history
    })
    await websocket.send_text(history_payload)

async def broadcast_user_list():
    # Faol ulanganlar va AI botni qo'shib yuboramiz
    users_list = list(active_connections.keys())
    if AI_BOT_NAME not in users_list:
        users_list.append(AI_BOT_NAME)
        
    payload = json.dumps({
        "type": "users_update",
        "users": users_list
    })
    for ws in active_connections.values():
        await ws.send_text(payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)