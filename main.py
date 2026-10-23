import os
import json
import urllib.request
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask
import threading

TOKEN = os.environ.get("8661640585:AAFkGTh4Ose1dZXti2J7vVfQvTueWagzYKU")

# ===== PHẦN GIỮ CỔNG WEB CHO RENDER =====
app_web = Flask(__name__)

@app_web.route('/')
def health():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# ===== LẤY GIÁ TỪ COINBASE (Không bị chặn) =====
def get_price(symbol):
    try:
        # 1. Lấy giá hiện tại
        url_ticker = f"https://api.exchange.coinbase.com/products/{symbol}-USD/ticker"
        req = urllib.request.Request(url_ticker, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            price = float(d["price"])
        
        # 2. Lấy thống kê 24h (High, Low, Volume)
        url_stats = f"https://api.exchange.coinbase.com/products/{symbol}-USD/stats"
        req_stats = urllib.request.Request(url_stats, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_stats, timeout=10) as r:
            s = json.loads(r.read())
            high = float(s["high"])
            low = float(s["low"])
            volume = float(s["volume"]) * price
            open_price = float(s["open"])
            change = ((price - open_price) / open_price) * 100

        return {"price": price, "change": change, "high": high, "low": low, "volume": volume}
    except Exception as e:
        return None

# ===== RSI (Dùng nến Coinbase) =====
def get_rsi(symbol, interval="1h"):
    try:
        # Lấy 100 nến 1h
        url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles?granularity=3600"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        
        # Coinbase trả về mảng [time, low, high, open, close, volume]
        # Sắp xếp lại theo thời gian tăng dần
        data = sorted(data, key=lambda x: x[0])
        closes = [float(k[4]) for k in data]
        
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(max(diff, 0)); losses.append(max(-diff, 0))
            
        # Tính RSI 14 phiên
        ag = sum(gains[-14:])/14; al = sum(losses[-14:])/14
        if al == 0: return 100
        return round(100 - (100/(1 + ag/al)), 1)
    except: return None

# ===== PHÂN TÍCH =====
def analyze(symbol):
    p = get_price(symbol)
    if not p: return "❌ Không lấy được dữ liệu từ Coinbase. Vui lòng thử lại sau."
    rsi = get_rsi(symbol); price = p["price"]
    
    if rsi and rsi < 35:
        sig = "🟢 LONG (oversold)"; entry = price
        sl = round(price*0.97,2); tp1 = round(price*1.03,2); tp2 = round(price*1.05,2)
    elif rsi and rsi > 65:
        sig = "🔴 SHORT (overbought)"; entry = price
        sl = round(price*1.03,2); tp1 = round(price*0.97,2); tp2 = round(price*0.95,2)
    else:
        sig = "⚪ CHỜ (trung tính)"; entry = price
        sl = round(price*0.98,2); tp1 = round(price*1.02,2); tp2 = round(price*1.04,2)
    
    return f"""📊 *{symbol}* — {sig}

💰 Giá: `{price:,.2f}` USD
📈 24h: `{p['change']:+.2f}%`
🔺 High: `{p['high']:,.2f}` | 🔻 Low: `{p['low']:,.2f}`
📊 Volume 24h: `${p['volume']/1e6:.1f}M`
💡 RSI(1h): `{rsi if rsi else 'N/A'}`

━━━━━━━━━━━━━━
🎯 *KẾ HOẠCH THAM KHẢO*
• Entry: `{entry:,.2f}`
• SL: `{sl:,.2f}`
• TP1: `{tp1:,.2f}`
• TP2: `{tp2:,.2f}`

⚠️ Chỉ tham khảo, không phải lời khuyên đầu tư.
🕐 {datetime.now().strftime('%H:%M %d/%m/%Y')}"""

# ===== HANDLERS =====
async def start(update: Update, ctx):
    await update.message.reply_text(
        "🤖 *Bot Crypto*\n/btc — Phân tích BTC\n/eth — Phân tích ETH\n/both — Cả hai\n/price — Giá nhanh",
        parse_mode="Markdown")

async def btc(update: Update, ctx):
    await update.message.reply_text(analyze("BTC"), parse_mode="Markdown")

async def eth(update: Update, ctx):
    await update.message.reply_text(analyze("ETH"), parse_mode="Markdown")

async def both(update: Update, ctx):
    await update.message.reply_text(analyze("BTC"), parse_mode="Markdown")
    await update.message.reply_text(analyze("ETH"), parse_mode="Markdown")

async def price(update: Update, ctx):
    b = get_price("BTC"); e = get_price("ETH")
    msg = "⚡ *Giá nhanh*\n\n"
    if b: msg += f"₿ BTC: `${b['price']:,.2f}` ({b['change']:+.2f}%)\n"
    if e: msg += f"Ξ ETH: `${e['price']:,.2f}` ({e['change']:+.2f}%)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===== MAIN =====
def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("both", both))
    app.add_handler(CommandHandler("price", price))
    app.run_polling()

if __name__ == "__main__":
    main()