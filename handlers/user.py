"""
CharglyBot V3 — معالجات المستخدم العامة
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from core.config  import SUPPORT_LINK
from database     import upsert_user, get_user_orders
from handlers.keyboards import kb_main
from handlers.messages  import WELCOME, SUPPORT_MSG, NO_ORDERS, fmt_order_row


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    u = update.effective_user
    await upsert_user(u.id, u.username, u.full_name)
    await update.message.reply_text(
        WELCOME, parse_mode="Markdown", reply_markup=kb_main()
    )
    return ConversationHandler.END


async def btn_support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        SUPPORT_MSG.format(support=SUPPORT_LINK),
        parse_mode="Markdown",
    )


async def btn_my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    orders = await get_user_orders(update.effective_user.id)
    if not orders:
        await update.message.reply_text(NO_ORDERS, parse_mode="Markdown")
        return
    text = "📦 *آخر طلباتك:*\n\n" + "".join(fmt_order_row(o) for o in orders)
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=kb_main()
    )


async def fallback_unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "استخدم الأزرار أدناه 👇", reply_markup=kb_main()
    )
