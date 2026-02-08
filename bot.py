from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import *
from database import cursor, conn
from indicators import analyze_market
from auto_engine import run_auto_engine
from datetime import datetime, timedelta
import asyncio

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, 0, NULL, 0)",
                   (user.id, user.username))
    conn.commit()

    kb = [
        [InlineKeyboardButton("📈 Auto Mode", callback_data="auto")],
        [InlineKeyboardButton("🎯 Manual Mode", callback_data="manual")],
        [InlineKeyboardButton("💎 VIP Upgrade", callback_data="vip")]
    ]
    await update.message.reply_text("Welcome to CRUXIFEED 💎", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "auto":
        await q.edit_message_text("Auto Mode Active — 5–12 trades/day")

    elif q.data == "manual":
        buttons = [[InlineKeyboardButton(p, callback_data=f"pair_{p}")] for p in PAIRS]
        await q.edit_message_text("Select Pair:", reply_markup=InlineKeyboardMarkup(buttons))

    elif "pair_" in q.data:
        context.user_data["pair"] = q.data.replace("pair_", "")
        buttons = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in TIMEFRAMES]
        await q.edit_message_text("Select Timeframe:", reply_markup=InlineKeyboardMarkup(buttons))

    elif "time_" in q.data:
        pair = context.user_data.get("pair")
        signal, confidence = analyze_market(pair)

        image = BUY_IMAGE_PATH if signal == "BUY" else SELL_IMAGE_PATH

        msg = f"""
CRUXIFEED — Manual Signal 💎

Pair: {pair}
Direction: {signal}
Confidence: {confidence}%

Indicators confirm momentum.
Execute trade now.
"""
        await q.message.reply_photo(InputFile(image), caption=msg)

    elif q.data == "vip":
        await q.edit_message_text(f"VIP Access — ${VIP_PRICE}/month\nSend payment proof to activate.")

async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute("INSERT INTO payments VALUES (?, ?, CURRENT_TIMESTAMP)",
                   (user.id, user.username))
    conn.commit()

    await context.bot.send_message(
        chat_id=f"@{ADMIN_USERNAME}",
        text=f"📩 VIP Payment Proof from @{user.username} | ID: {user.id}"
    )

    await update.message.reply_text("Payment proof received. Await approval.")

async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != ADMIN_USERNAME:
        return

    user_id = int(context.args[0])
    expiry = (datetime.now() + timedelta(days=VIP_DAYS)).strftime("%Y-%m-%d")

    cursor.execute("UPDATE users SET vip = 1, vip_expiry = ? WHERE user_id = ?",
                   (expiry, user_id))
    conn.commit()

    await update.message.reply_text(f"VIP Activated until {expiry}")

async def vip_checker(context):
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET vip = 0 WHERE vip_expiry < ?", (today,))
    conn.commit()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addvip", addvip))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.PHOTO, payment_handler))

app.job_queue.run_repeating(vip_checker, interval=3600)
app.job_queue.run_repeating(lambda ctx: run_auto_engine(ctx.bot), interval=10)

app.run_polling()