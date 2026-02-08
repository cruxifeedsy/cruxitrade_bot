import random, asyncio
from indicators import analyze_market
from config import *
from telegram import InputFile

async def run_auto_engine(bot):
    trades_today = 0
    daily_limit = random.randint(MIN_AUTO_TRADES, MAX_AUTO_TRADES)

    while True:
        if trades_today >= daily_limit:
            await asyncio.sleep(3600)
            trades_today = 0

        pair = random.choice(PAIRS)
        signal, confidence = analyze_market(pair)

        await bot.send_message(
            chat_id=f"@{ADMIN_USERNAME}",
            text=f"📌 NOTICE — {pair} expires in 1 minute"
        )

        await asyncio.sleep(AUTO_SIGNAL_DELAY)

        image = BUY_IMAGE_PATH if signal == "BUY" else SELL_IMAGE_PATH

        await bot.send_photo(
            chat_id=f"@{ADMIN_USERNAME}",
            photo=InputFile(image),
            caption=f"""
CRUXIFEED — Auto Signal 💎

Pair: {pair}
Direction: {signal}
Confidence: {confidence}%

Execute trade now.
"""
        )

        trades_today += 1
        await asyncio.sleep(random.randint(900, 1800))