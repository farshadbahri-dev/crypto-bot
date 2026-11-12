import time
import requests
import pandas as pd
import numpy as np

# --- تنظیمات اختصاصی شما (ثبت شده) ---
TELEGRAM_TOKEN = "9239244106:AAFARbsq96cVXd3RkpwKHuyQpd-ctppYrkI"
CHAT_ID = "68528061" 
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

# دریافت داده‌های کندل و فاندینگ‌ریت (داده‌های مشتقات مشابه کوین‌گلس)
def get_market_data(symbol):
    # ۱. دریافت کندل‌های ۱۵ دقیقه‌ای فیوچرز
    klines_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit=100"
    data = requests.get(klines_url).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qv', 'tr', 'tb', 'tq', 'ig'])
    df[['open', 'high', 'low', 'close', 'vol']] = df[['open', 'high', 'low', 'close', 'vol']].astype(float)
    
    # ۲. دریافت فاندینگ ریت لحظه‌ای (شاخص کلیدی کوین‌گلس)
    funding_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
    funding_data = requests.get(funding_url).json()
    funding_rate = float(funding_data['lastFundingRate']) * 100
    
    return df, funding_rate

def calculate_indicators(df):
    # میانگین متحرک ۵۰ (تشخیص روند)
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # محاسبه RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def scan_and_signal():
    for symbol in SYMBOLS:
        try:
            df, funding = get_market_data(symbol)
            df = calculate_indicators(df)
            
            last = df.iloc[-1]
            recent_low = df['low'].iloc[-20:-1].min()
            recent_high = df['high'].iloc[-20:-1].max()
            
            price = last['close']
            ema50 = last['EMA50']
            rsi = last['RSI']
            
            # تشخیص شکار نقدینگی (Sweep)
            swept_low = (last['low'] < recent_low) and (price > recent_low)
            swept_high = (last['high'] > recent_high) and (price < recent_high)
            
            # --- استراتژی ترکیبی وین‌ریت بالا ---
            # شرط خرید: روند صعودی + (اصلاح RSI یا جاروی کف) + عدم اشباع فاندینگ‌ریت خرید
            if ((price > ema50 and rsi < 40) or swept_low) and (funding < 0.03):
                sl = min(recent_low, price * 0.992)
                tp = price + ((price - sl) * 1.5)
                msg = (
                    f"🟢 **سیگنال خرید (LONG) - {symbol}**\n\n"
                    f"📍 **نقطه ورود:** `{price:.2f}`\n"
                    f"🛑 **حد ضرر (SL):** `{sl:.2f}`\n"
                    f"🎯 **حد سود (TP):** `{tp:.2f}`\n\n"
                    f"📊 **دلایل تایید:**\n"
                    f"• RSI در ناحیه بهینه ({rsi:.1f})\n"
                    f"• فاندینگ ریت متعادل ({funding:.4f}%)\n"
                    f"• تایید ساختار روند / نقدینگی"
                )
                send_telegram_alert(msg)
            
            # شرط فروش: روند نزولی + (اصلاح RSI یا جاروی سقف) + عدم اشباع فاندینگ‌ریت فروش
            elif ((price < ema50 and rsi > 60) or swept_high) and (funding > -0.03):
                sl = max(recent_high, price * 1.008)
                tp = price - ((sl - price) * 1.5)
                msg = (
                    f"🔴 **سیگنال فروش (SHORT) - {symbol}**\n\n"
                    f"📍 **نقطه ورود:** `{price:.2f}`\n"
                    f"🛑 **حد ضرر (SL):** `{sl:.2f}`\n"
                    f"🎯 **حد سود (TP):** `{tp:.2f}`\n\n"
                    f"📊 **دلایل تایید:**\n"
                    f"• RSI در اشباع خرید ({rsi:.1f})\n"
                    f"• فاندینگ ریت متعادل ({funding:.4f}%)\n"
                    f"• تایید مقاومت / جاروی نقدینگی"
                )
                send_telegram_alert(msg)
                
        except Exception as e:
            print(f"خطا در بررسی {symbol}: {e}")

# اجرای مداوم هر ۵ دقیقه یک‌بار
if __name__ == "__main__":
    send_telegram_alert("🤖 ربات تحلیل‌گر هوشمند BTC و ETH فعال شد و به حساب فرشاد متصل گردید!")
    while True:
        scan_and_signal()
        time.sleep(300)
