import os
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime

class DanteCryptoBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.is_running = False
        
    def fetch_coingecko_data(self):
        """Fetch crypto data from CoinGecko API"""
        try:
            trending_url = "https://api.coingecko.com/api/v3/search/trending"
            with urllib.request.urlopen(trending_url) as response:
                trending_data = json.loads(response.read().decode())
            
            global_url = "https://api.coingecko.com/api/v3/global"
            with urllib.request.urlopen(global_url) as response:
                global_data = json.loads(response.read().decode())
            
            return {
                'trending': trending_data,
                'global': global_data,
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"Error fetching CoinGecko data: {e}")
            return None
    
    def format_crypto_article(self, data):
        """Format data into 50-80 word article"""
        if not data:
            return "📊 <b>Crypto Market Update</b>\n\nMarket data temporarily unavailable. Will retry shortly!"
        
        trending_coins = data['trending']['coins'][:3]
        global_info = data['global']['data']
        
        article = f"🚀 <b>Crypto Pulse - {data['timestamp'].strftime('%d %b, %H:%M IST')}</b>\n\n"
        
        article += "📈 <b>Trending Now:</b>\n"
        for i, coin_data in enumerate(trending_coins, 1):
            coin = coin_data['item']
            article += f"{i}. {coin['name']} ({coin['symbol'].upper()})\n"
        
        total_cap = global_info.get('total_market_cap', {}).get('usd', 0)
        if total_cap:
            cap_trillion = total_cap / 1_000_000_000_000
            article += f"\n💰 Global Cap: ${cap_trillion:.2f}T"
        
        btc_dominance = global_info.get('market_cap_percentage', {}).get('btc', 0)
        if btc_dominance:
            article += f" | BTC Dom: {btc_dominance:.1f}%"
        
        article += "\n\n🎯 <i>Trade wisely, manage risk!</i>"
        
        return article
    
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            data_encoded = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                if result.get('ok'):
                    print(f"✓ Message sent successfully at {datetime.now().strftime('%H:%M:%S')}")
                    return True
                else:
                    print(f"✗ Failed to send message: {result}")
                    return False
                    
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def update_cycle(self):
        """Single update cycle - fetch and send data"""
        print(f"🔄 Fetching crypto data... {datetime.now().strftime('%H:%M:%S')}")
        
        crypto_data = self.fetch_coingecko_data()
        
        if crypto_data:
            article = self.format_crypto_article(crypto_data)
            success = self.send_telegram_message(article)
            
            if success:
                print("✅ Update cycle completed successfully")
            else:
                print("❌ Failed to send update")
        else:
            print("❌ Failed to fetch crypto data")
    
    def start_bot(self, interval_minutes=15):
        """Start the bot with specified interval"""
        self.is_running = True
        print(f"🤖 Dante Crypto Bot started! Updates every {interval_minutes} minutes")
        print(f"📱 Sending to chat ID: {self.chat_id}")
        
        startup_msg = "🤖 <b>Dante Crypto Bot Activated!</b>\n\n📊 Starting automated crypto updates every 15 minutes.\n\n🚀 Stay tuned for trending coins and market insights!"
        self.send_telegram_message(startup_msg)
        
        while self.is_running:
            try:
                self.update_cycle()
                
                print(f"⏱️ Waiting {interval_minutes} minutes for next update...")
                for _ in range(interval_minutes * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                print("⏱️ Retrying in 60 seconds...")
                time.sleep(60)
        
        self.is_running = False
        print("🤖 Dante Crypto Bot stopped")
    
    def stop_bot(self):
        """Stop the bot"""
        self.is_running = False

if __name__ == "__main__":
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ ERROR: Please set BOT_TOKEN and CHAT_ID environment variables before running the bot.")
        exit(1)
    
    try:
        CHAT_ID = int(CHAT_ID)
    except ValueError:
        print("❌ ERROR: CHAT_ID should be a number.")
        exit(1)
    
    dante = DanteCryptoBot(BOT_TOKEN, CHAT_ID)
    dante.start_bot(interval_minutes=15)
