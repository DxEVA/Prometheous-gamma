import os
import threading
import statistics
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
    return "Dante Bot is alive!", 200

def run_flask():
    app.run(host="0.0.0.0", port=10000)

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
                f"• <b>{name} ({symbol})</b>\n"
                f"Price: ${price:,}\n"
                f"24h High: ${high_24h:,} | 24h Low: ${low_24h:,}\n"
                f"Rank: {rank}\n\n"
            )
        else:
            msg += f"• <b>{name} ({symbol})</b> Rank: {rank} (data unavailable)\n\n"
    return msg

def fetch_obv_and_avg(symbol):
    try:
        candles = cg.get_coin_ohlc_by_id(symbol, vs_currency='usd', days=127)
        if not candles or len(candles) < 2:
            return None, None
        closes = [candle[4] for candle in candles]
        avg_price = statistics.mean(closes)
        volumes = [candle[5] if len(candle) > 5 else 0 for candle in candles]
        obv = sum(volumes)  # simplification of OBV
        return obv, avg_price
    except Exception as e:
        print("Error fetching OBV/Avg:", e)
        return None, None

def format_coin_details(symbol):
    try:
        market = cg.get_coins_markets(vs_currency='usd', ids=symbol.lower())
        if not market:
            return f"No data found for symbol: {symbol}"
        coin = market[0]
        global_stats = cg.get_global()['data']
        btc_dom = global_stats.get('market_cap_percentage', {}).get('btc', 0)
        obv, avg_price = fetch_obv_and_avg(symbol.lower())
        details = (
            f"📊 <b>{coin['name']} ({coin['symbol'].upper()})</b>\n"
            f"Price: ${coin['current_price']:,}\n"
            f"Market Cap: ${coin['market_cap']:,}\n"
            f"24h Volume: ${coin['total_volume']:,}\n"
            f"24h High / Low: ${coin['high_24h']:,} / ${coin['low_24h']:,}\n"
            f"BTC Dominance: {btc_dom:.2f}%\n"
        )
        if obv is not None and avg_price is not None:
            details += f"Approx. OBV: {obv:,.0f}\nAvg Price (127d): ${avg_price:,.2f}\n"
        details += f"More info: https://www.coingecko.com/en/coins/{coin['id']}"
        return details
    except Exception as e:
        return f"Error retrieving details for {symbol}: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = (
        "🤖 Dante Bot - Commands:\n"
        "/update - Top 7 trending coins (unchanged)\n"
        "/detail <coin1> [coin2 ... up to 5] - Details incl. BTC dominance, OBV, avg price\n"
        "/global - Global crypto market stats\n"
        "/losers - Top 7 losers in 24h"
    )
    await update.message.reply_html(commands)

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = format_trending()
    await update.message.reply_html(msg)

async def detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args[:5]
    if not args:
        await update.message.reply_text("Please specify 1 to 5 coin IDs, e.g. /detail bitcoin ethereum")
        return
    for sym in args:
        reply = format_coin_details(sym)
        await update.message.reply_html(reply)

async def global_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        info = cg.get_global()['data']
        msg = (
            "<b>🌐 Global Crypto Market Stats</b>\n"
            f"Market Cap: ${info['total_market_cap']['usd']:,}\n"
            f"24h Volume: ${info['total_volume']['usd']:,}\n"
            f"BTC Dominance: {info['market_cap_percentage']['btc']:.2f}%\n"
            f"ETH Dominance: {info['market_cap_percentage']['eth']:.2f}%\n"
            f"Active Cryptos: {info['active_cryptocurrencies']}"
        )
        await update.message.reply_html(msg)
    except Exception as e:
        await update.message.reply_text("Failed to fetch global stats: " + str(e))

async def losers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        coins = cg.get_coins_markets(vs_currency='usd', order='price_change_percentage_24h_asc', per_page=7, page=1)
        msg = "📉 <b>Top 7 Losers (24h)</b>\n\n"
        for i, coin in enumerate(coins, 1):
            msg += f"{i}. {coin['name']} ({coin['symbol'].upper()}) {coin['price_change_percentage_24h']:.2f}% (${coin['current_price']:,})\n"
        await update.message.reply_html(msg)
    except Exception as e:
        await update.message.reply_text("Failed to fetch losers: " + str(e))

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("detail", detail_command))
    app.add_handler(CommandHandler("global", global_command))
    app.add_handler(CommandHandler("losers", losers_command))
    app.run_polling()

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Set BOT_TOKEN and CHAT_ID environment variables before running!")
        exit(1)
    
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
