import os
import threading
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pycoingecko import CoinGeckoAPI

app = Flask(__name__)
cg = CoinGeckoAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

@app.route("/")
def health_check():
    return "Dante Bot is running!", 200

def run_flask():
    # Run Flask app for Render health checks
    app.run(host="0.0.0.0", port=10000)

# Telegram bot command handlers and helpers 

def format_trending():
    trending = cg.get_search_trending()
    coins = trending['coins'][:7]
    ids = [item['item']['id'] for item in coins if 'item' in item]
    market_data = cg.get_coins_markets(vs_currency='usd', ids=",".join(ids))
    market_map = {coin['id']: coin for coin in market_data}
    msg = "🚀 <b>Trending Crypto Alert (Top 7)</b>\n\n"
    for i, c in enumerate(coins, 1):
        item = c['item']
        coin_id = item['id']
        name = item['name']
        symbol = item['symbol'].upper()
        rank = item.get('market_cap_rank', 'N/A')
        market = market_map.get(coin_id)
        if market:
            price = market.get('current_price', 'N/A')
            high_24h = market.get('high_24h', 'N/A')
            low_24h = market.get('low_24h', 'N/A')
            msg += (
                f"{i}. <b>{name}</b> ({symbol}) - Rank: {rank}\n"
                f"   Price: ${price}\n"
                f"   24h High: ${high_24h}\n"
                f"   24h Low: ${low_24h}\n\n"
            )
        else:
            msg += f"{i}. <b>{name}</b> ({symbol}) - Rank: {rank} (data unavailable)\n\n"
    return msg

def format_coin_details(symbol):
    try:
        result = cg.get_coins_markets(vs_currency='usd', ids=symbol.lower())
        if not result:
            return f"No data found for symbol: {symbol}"
        coin = result[0]
        msg = (
            f"📊 <b>{coin['name']} ({coin['symbol'].upper()})</b>\n"
            f"Current Price: ${coin['current_price']}\n"
            f"Market Cap: ${coin['market_cap']:,}\n"
            f"24h Volume: ${coin['total_volume']:,}\n"
            f"High 24h: ${coin['high_24h']}\n"
            f"Low 24h: ${coin['low_24h']}\n"
            f"Link: https://www.coingecko.com/en/coins/{coin['id']}\n"
        )
        return msg
    except Exception as e:
        return "Failed to get details: " + str(e)

# Additional helper commands omitted for brevity; use previous example command handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "🤖 Dante Advanced Bot Ready!\n"
        "Commands:\n"
        "/update - Top 7 Trending + 24h High/Low\n"
        "/detail <coin_id> - Details for a coin\n"
        # Add other commands similarly
    )

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = format_trending()
    await update.message.reply_html(msg)

async def detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        symbol = context.args[0]
        msg = format_coin_details(symbol)
    else:
        msg = "Please provide a coin id, e.g. /detail bitcoin"
    await update.message.reply_html(msg)

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("detail", detail_command))
    # Add other handlers as needed
    app.run_polling()

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ ERROR: Please set BOT_TOKEN and CHAT_ID environment variables.")
        exit(1)
    try:
        CHAT_ID_int = int(CHAT_ID)
    except ValueError:
        print("❌ ERROR: CHAT_ID should be numeric.")
        exit(1)

    # Run Flask server for health checks in background thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Run Telegram bot (blocking call)
    run_bot()
