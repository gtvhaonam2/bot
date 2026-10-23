import os
import requests
import json
import urllib.request
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8661640585:AAFkGTh4Ose1dZXti2J7vVfQvTueWagzYKU")

# ===== GIÁ =====
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
        return {"price": float(d["lastPrice"]), "change": float(d["priceChangePercent"]),
                "high": float(d["highPrice"]), "low": float(d["lowPrice"]),
                "volume": float(d["quoteVolume"])}
    except: return None

# ===== RSI =====
def get_rsi(symbol, interval="1h"):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=100"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        closes = [float(k[4]) for k in data]
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(max(diff, 0)); losses.append(max(-diff, 0))
        ag = sum(gains[-14:])/14; al = sum(losses[-14:])/14
        if al == 0: return 100
        return round(100 - (100/(1 + ag/al)), 1)
    except: return None

# ===== PHÂN TÍCH =====
def analyze(symbol):
    p = get_price(symbol)
    if not p: return "❌ Không lấy được dữ liệu."
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

💰 Giá: `{price:,.2f}` USDT
📈 24h: `{p['change']:+.2f}%`
🔺 High: `{p['high']:,.2f}` | 🔻 Low: `{p['low']:,.2f}`
📊 Volume: `${p['volume']/1e6:.1f}M`
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
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("both", both))
    app.add_handler(CommandHandler("price", price))
    app.run_polling()

if __name__ == "__main__":
    main()
