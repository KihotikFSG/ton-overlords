import sqlite3
import time
import random
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="TON Overlords: Ultimate MMO Engine")

# Полный CORS для работы в облаке
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("game_empire.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            race TEXT DEFAULT NULL,
            gold REAL DEFAULT 100.0,
            crystal REAL DEFAULT 20.0,
            iron REAL DEFAULT 0.0,
            prod_gold REAL DEFAULT 1.0,
            prod_iron REAL DEFAULT 0.0,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

class ChooseRace(BaseModel):
    user_id: int
    race: str

@app.get("/api/get_profile/{user_id}")
def get_profile(user_id: int):
    conn = sqlite3.connect("game_empire.db")
    cursor = conn.cursor()
    cursor.execute("SELECT race, gold, crystal, iron, prod_gold, prod_iron, level, xp FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row: return {"race": None}
    return {"race": row[0], "gold": row[1], "crystal": row[2], "iron": row[3], "prod_gold": row[4], "prod_iron": row[5], "level": row[6], "xp": row[7]}

@app.post("/api/choose_race")
def choose_race(data: ChooseRace):
    conn = sqlite3.connect("game_empire.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO players (user_id, username, race, gold, crystal, iron, prod_gold, prod_iron, level, xp)
        VALUES (?, 'Игрок', ?, 100.0, 20.0, 0.0, 1.0, 0.0, 1, 0)
    """, (data.user_id, data.race))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/player/add_xp")
def add_xp(data: dict):
    conn = sqlite3.connect("game_empire.db")
    cursor = conn.cursor()
    cursor.execute("SELECT level, xp FROM players WHERE user_id = ?", (data["user_id"],))
    row = cursor.fetchone()
    if not row: return {"leveled_up": False}
    lvl, xp = row
    xp += data["xp_amount"]
    needed = (lvl ** 2) * 100
    leveled_up = False
    if xp >= needed:
        xp -= needed
        lvl += 1
        leveled_up = True
    cursor.execute("UPDATE players SET level = ?, xp = ? WHERE user_id = ?", (lvl, xp, data["user_id"]))
    conn.commit()
    conn.close()
    return {"leveled_up": leveled_up, "current_level": lvl}

@app.post("/api/ai/chat")
async def ai_chat_respond(user_id: int, user_message: str):
    msg = user_message.lower()
    if "подземелье" in msg or "катакомбы" in msg:
        ai_text = "🧙‍♂️ *Хозяин Таверны шепчет*: 'Катакомбы смертельно опасны, путник! Хватай свой меч, двигайся по стрелкам джойстика и уничтожай монстров [🎯]. За каждого моба я лично отсыплю тебе золота и опыта!'"
    elif "раса" in msg or "фракция" in msg:
        ai_text = "🧙‍♂️ *Хозяин Таверны*: 'В нашем мире 6 великих рас: Люди, Эльфы, Орки, Гномы, Охотники и Древоходы. Твой выбор определит твою судьбу в Войне Сезонов за призовой фонд TON!'"
    elif "бур" in msg or "добыча" in msg:
        ai_text = "🧙‍♂️ *Хозяин Таверны*: 'Твой... Бур изрыгает чистую энергию! Кликай по нему чаще — это приносит Кристаллы и Опыт. Не забывай собирать ресурсы вовремя!'"
    else:
        ai_text = "🧙‍♂️ *Хозяин Таверны протирает кружку*: 'Рад видеть тебя в столице, воин! Пока твои рабочие добывают железо, а отряды штурмуют катакомбы, выпей эля. Спрашивай меня обо всем — лор игры, крафт или PvP дуэли!'"
    return {"sender": "🧙‍♂️ Хозяин Таверны", "text": ai_text}

online_heroes = {}
chat_sessions = {}

@app.websocket("/ws/mmo_hub")
async def websocket_mmo_hub(websocket: WebSocket):
    await websocket.accept()
    online_heroes[websocket] = {"user_id": random.randint(1000,9999), "username": "Игрок", "x": 700, "y": 600, "action": "idle"}
    try:
        while True:
            data_str = await websocket.receive_text()
            packet = json.loads(data_str)
            if packet["type"] == "move":
                online_heroes[websocket].update({"x": packet["x"], "y": packet["y"], "action": "moving"})
            elif packet["type"] == "dance":
                online_heroes[websocket]["action"] = "dancing"
            broadcast_packet = json.dumps({"type": "sync", "players": list(online_heroes.values())})
            for ws in online_heroes.keys():
                try: await ws.send_text(broadcast_packet)
                except Exception: pass
    except WebSocketDisconnect: del online_heroes[websocket]

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    uid = random.randint(1000,9999)
    chat_sessions[uid] = {"ws": websocket, "username": f"Puti_n_{random.randint(10,99)}"}
    try:
        while True:
            msg_str = await websocket.receive_text()
            packet = json.loads(msg_str)
            out_packet = json.dumps({"channel": packet["channel"], "sender": chat_sessions[uid]["username"], "text": packet["text"]})
            for session in chat_sessions.values():
                try: await session["ws"].send_text(out_packet)
                except Exception: pass
    except WebSocketDisconnect: del chat_sessions[uid]
