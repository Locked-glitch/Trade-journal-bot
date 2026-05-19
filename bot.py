from flask import Flask, request
import requests
import psycopg2
from datetime import datetime
import os

tik = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
app = Flask(__name__)


def reply_message(chat_id, reply):

    url = f"https://api.telegram.org/bot{tik}/sendMessage"

    requests.post(url, json={
        "chat_id": chat_id,
        "text": reply
    })


# CREATE DATABASE
def init_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_trades (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT,
        date TEXT,
        pair TEXT,
        day TEXT,
        take_profit REAL,
        stop_loss REAL,
        result TEXT,
        duration TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route(f"/{tik}", methods=["POST"])
def journal():

    data = request.get_json()

    message = data.get("message")

    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()
    user = message["from"]
    username = user.get("first_name", "user")
    parts = text.split()
    if text == "/start":
        reply = (
            f"📘 Welcome, {username}!\n\n"
            f"I’m your personal Trade Journal Bot.\n"
            f"Track your trades, review performance, "
            f"and stay disciplined like a professional trader 📈\n\n"
            f"⚡ Quick Commands:\n"
            f"/dashboard - View all trades\n"
            f"/help - Usage guide\n\n"
            f"📝 Trade Format:\n"
            f"Pair Day TP SL Result Duration\n\n"
            f"Example:\n"
            f"BTCUSDT Monday 120 50 WIN 2h"
        )
        reply_message(chat_id, reply)

    elif text == "/dashboard":
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM log_trades WHERE chat_id = %s",
            (chat_id,)
        )

        data = cursor.fetchall()
        reply_message(chat_id, f"📊 Total Trades: {len(data)}\n")

        if not data:
            reply_message(
                chat_id,
                "📭 No trades found yet.\n\nStart journaling your trades to build your trading history."
            )
        for index, row in enumerate(data, start=1):
            trade_id, user_chat_id, date, pair, day, tp, sl, result, duration = row

            status = "🟢 WIN" if result.upper() == "WIN" else "🔴 LOSS"
            reply = (
                f"📊 Trade #{index}\n\n"
                f"📅 Date: {date}\n"
                f"💱 Pair: {pair}\n"
                f"📆 Day: {day}\n\n"

                f"🟢 TP: +{tp}%\n"
                f"🔴 SL: -{sl}%\n\n"

                f"⏱ Duration: {duration}\n"
                f"📈 Result: {status}\n"
            )
            reply_message(chat_id, reply)
            
    elif text == "/help":
        reply = (
            "🛠 Trade Journal Help Center\n\n"

            "📌 Commands:\n"
            "/start - Launch the bot\n"
            "/dashboard - View saved trades\n"
            "/help - Show help menu\n\n"

            "📝 How To Save a Trade:\n"
            "Send your trade in this format:\n\n"

            "Pair Day TP SL Result Duration\n\n"

            "✅ Example:\n"
            "BTCUSDT Monday 120 50 WIN 2h\n\n"

            "📖 Meaning:\n"
                "• Pair → Trading pair\n"
                "• Day → Trade day\n"
                "• TP → Take Profit\n"
                "• SL → Stop Loss\n"
                "• Result → WIN or LOSS\n"
                "• Duration → Trade holding time\n\n"
                
                "⏱ Examples:\n"
                "• 15m → 15 minutes\n"
                "• 2h → 2 hours\n"
                "• 1d → 1 day"
        )
        reply_message(chat_id, reply)
    else:
        if text.startswith("/"):
            reply_message(
                chat_id,
                "❌ Unknown command.\nUse /help to see available commands."
            )
            return "ok"
        try:

            pair = parts[0]
            day = parts[1]

            tp = float(parts[2])
            sl = float(parts[3])

            res = parts[4]
            duration = parts[5]
            now = datetime.now().strftime("%Y-%m-%d")

            # NEW CONNECTION EACH REQUEST
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO log_trades
            (chat_id, date, pair, day, take_profit, stop_loss, result, duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (chat_id, now, pair, day, tp, sl, res, duration))

            conn.commit()
            conn.close()

            reply_message(
                chat_id,
                "✅ Trade saved successfully.\n\nYour journal has been updated 📘"
            )

        except IndexError:

            reply_message(
                chat_id,
                "⚠️ Invalid trade format.\n\n"
                "Use this structure:\n"
                "Pair Day TP SL Result Duration\n\n"
                "✅ Example:\n"
                "BTCUSDT Monday 120 50 WIN 2h"
            )

        except ValueError:

            reply_message(
                chat_id,
                "⚠️ Invalid TP or SL value.\n\n"
                "Take Profit and Stop Loss must be numeric values.\n\n"
                "✅ Example:\n"
                "BTCUSDT Monday 120 50 WIN 2h"
            )
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
