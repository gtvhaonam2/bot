import os
import sqlite3
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uvicorn

# LẤY TOKEN TỪ BIẾN MÔI TRƯỜNG (Sẽ điền ở Bước 3)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8661640585:AAFkGTh4Ose1dZXti2J7vVfQvTueWagzYKU")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI()

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, subscribed INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

init_db()

def send_telegram(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

@app.get("/")
def read_root():
    return {"status": "Bot đang chạy!"}

# NHẬN LỆNH TỪ TELEGRAM
@app.get("/telegram_webhook")
def telegram_webhook(update: dict):
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        if text == "/start":
            cursor.execute("INSERT OR REPLACE INTO users (chat_id, subscribed) VALUES (?, 1)", (chat_id,))
            conn.commit()
            send_telegram(chat_id, "✅ Bạn đã đăng ký nhận tín hiệu XAUUSD thành công!\nGõ /stop để hủy.")
        elif text == "/stop":
            cursor.execute("UPDATE users SET subscribed = 0 WHERE chat_id = ?", (chat_id,))
            conn.commit()
            send_telegram(chat_id, "🔕 Đã hủy đăng ký.")
        conn.close()
    return {"ok": True}

# NHẬN TÍN HIỆU TỪ TRADINGVIEW & BẮN TELEGRAM
def broadcast_signal(msg):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users WHERE subscribed = 1")
    users = cursor.fetchall()
    conn.close()
    for user in users:
        send_telegram(user[0], msg)

@app.post("/webhook")
async def tradingview_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    event = data.get("event")
    symbol = data.get("symbol", "XAUUSD")
    direction = data.get("direction")
    entry, sl, tp1, tp2, tp3 = data.get("entry"), data.get("sl"), data.get("tp1"), data.get("tp2"), data.get("tp3")
    score = data.get("score", 0)
    order_type = data.get("order_type", "MARKET")
    
    msg = ""
    if event == "ENTRY":
        emoji = "🟢" if direction == "BUY" else "🔴"
        msg = f"{emoji} <b>{symbol} {direction} (MARKET)</b>\n\n📍 Entry: {entry}\n🛑 SL: {sl}\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}\n🎯 TP3: {tp3}\n\n📊 Score: {score}/100"
    elif event == "NEW_LIMIT":
        emoji = "⏳"
        msg = f"{emoji} <b>{symbol} {direction} LIMIT (Dự đoán)</b>\n\n📍 Giá chờ: {entry}\n🛑 SL: {sl}\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}\n🎯 TP3: {tp3}"
    elif event == "LIMIT_TRIGGERED":
        msg = f"⚡️ <b>ĐÃ KHỚP LỆNH LIMIT!</b>\n\n{symbol} {direction} tại giá {entry}"
    elif event == "UPDATE":
        status = data.get("status")
        status_text = "Chạm TP/SL"
        if status == "TP1_HIT": status_text = "🎯 ĐÃ CHẠM TP1"
        elif status == "TP2_HIT": status_text = "🎯 ĐÃ CHẠM TP2"
        elif status == "TP3_HIT": status_text = "🏆 ĐÃ CHẠM TP3"
        elif status == "SL_HIT": status_text = "🛑 ĐÃ CHẠM STOPLOSS"
        msg = f"{status_text}\n\nLệnh: <b>{symbol} {direction}</b> ({order_type})"

    if msg:
        background_tasks.add_task(broadcast_signal, msg)
    return {"status": "success"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
