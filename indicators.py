import yfinance as yf
import pandas as pd

def analyze_market(pair):
    ticker = pair.replace("/", "") + "=X"
    data = yf.download(ticker, period="1d", interval="1m")

    if len(data) < 30:
        return "HOLD", 50

    close = data["Close"]

    rsi = 100 - (100 / (1 + close.pct_change().rolling(14).mean()))
    ema_fast = close.ewm(span=9).mean()
    ema_slow = close.ewm(span=21).mean()
    macd = ema_fast - ema_slow

    score = 0
    if rsi.iloc[-1] < 35: score += 1
    if rsi.iloc[-1] > 65: score += 1
    if ema_fast.iloc[-1] > ema_slow.iloc[-1]: score += 1
    if macd.iloc[-1] > 0: score += 1

    signal = "BUY" if score >= 3 else "SELL"
    confidence = 70 + score * 5

    return signal, confidence