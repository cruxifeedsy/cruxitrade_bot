from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import *
from database import cursor, conn
from indicators import analyze_market
from auto_engine import run_auto_engine
from datetime import datetime, timedelta
import asyncio

# ---------------- START COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user = update.message.from_user

    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, 0, NULL, 0)",
        (user.id, user.username)
    )
    conn.commit()

    kb = [
        [InlineKeyboardButton("📈 Auto Mode", callback_data="auto")],
        [InlineKeyboardButton("🎯 Manual Mode", callback_data="manual")],
        [InlineKeyboardButton("💎 VIP Upgrade", callback_data="vip")]
    ]

    await update.message.reply_text(
        "Welcome to CRUXIFEED 💎\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- BUTTON HANDLER ----------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q is None:
        return

    await q.answer()

    # AUTO MODE
    if q.data == "auto":
        await q.edit_message_text("Auto Mode Active — 5–12 trades/day")

    # MANUAL MODE
    elif q.data == "manual":
        pair_buttons = [[InlineKeyboardButton(p, callback_data=f"pair_{p}")] for p in PAIRS]
        await q.edit_message_text("Select Pair:", reply_markup=InlineKeyboardMarkup(pair_buttons))

    # PAIR SELECTED
    elif "pair_" in q.data:
        context.user_data["pair"] = q.data.replace("pair_", "")

        time_buttons = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in TIMEFRAMES]
        await q.edit_message_text("Select Timeframe:", reply_markup=InlineKeyboardMarkup(time_buttons))

    # TIMEFRAME SELECTED → ANALYZE
    elif "time_" in q.data:
        pair = context.user_data.get("pair")

        if not pair:
            await q.edit_message_text("Please select a pair again.")
            return

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

    # VIP PAGE
    elif q.data == "vip":
        await q.edit_message_text(
            f"VIP Access — ${VIP_PRICE}/month\nSend payment proof to activate."
        )

# ---------------- PAYMENT HANDLER ----------------
async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user = update.message.from_user

    cursor.execute(
        "INSERT INTO payments VALUES (?, ?, CURRENT_TIMESTAMP)",
        (user.id, user.username)
    )
    conn.commit()

    await context.bot.send_message(
        chat_id=f"@{ADMIN_USERNAME}",
        text=f"📩 VIP Payment Proof from @{user.username} | ID: {user.id}"
    )

    await update.message.reply_text("Payment proof received. Await approval.")

# ---------------- ADMIN VIP APPROVAL ----------------
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    if update.message.from_user.username != ADMIN_USERNAME:
        return

    if not context.args:
        await update.message.reply_text("Usage: /addvip USER_ID")
        return

    user_id = int(context.args[0])
    expiry = (datetime.now() + timedelta(days=VIP_DAYS)).strftime("%Y-%m-%d")

    cursor.execute(
        "UPDATE users SET vip = 1, vip_expiry = ? WHERE user_id = ?",
        (expiry, user_id)
    )
    conn.commit()

    await update.message.reply_text(f"VIP Activated until {expiry}")

# ---------------- VIP EXPIRY CHECK ----------------
async def vip_checker(context):
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET vip = 0 WHERE vip_expiry < ?", (today,))
    conn.commit()

# ---------------- MAIN BOT RUNNER ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addvip", addvip))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.PHOTO, payment_handler))

app.job_queue.run_repeating(vip_checker, interval=3600)
app.job_queue.run_repeating(lambda ctx: run_auto_engine(ctx.bot), interval=10)

app.run_polling()