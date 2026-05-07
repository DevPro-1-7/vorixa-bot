"""
CharglyBot V3 — مرحلة الدفع + إثبات الدفع

يُفعَّل فقط بعد موافقة الأدمن (callback pay:proof).
المستخدم يرسل صورة التحويل → يتحول لـ PAYMENT_SENT (Protected).
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from core.config  import ADMIN_ID, SUPPORT_LINK
from core.states  import STEP_PAY_PROOF
from database     import get_order, set_payment_proof
from handlers.keyboards import kb_admin_proof, kb_main
from handlers.messages  import (
    ASK_PROOF, PROOF_RECEIVED, ADMIN_PROOF_RECEIVED,
    NOT_PHOTO, now_str,
)
from handlers.charge import _extract_photo

log = logging.getLogger(__name__)


async def cb_pay_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """المستخدم يضغط 'لقد قمت بالدفع' → اطلب صورة الإثبات"""
    q = update.callback_query
    await q.answer()

    # استرجاع order_id من bot_data (خُزّن عند الموافقة)
    user_id  = update.effective_user.id
    order_id = ctx.bot_data.get("user_pending_payment", {}).get(user_id)

    if not order_id:
        await q.edit_message_text(
            "⚠️ لم يُعثر على الطلب. تواصل مع الدعم.", parse_mode="Markdown"
        )
        return ConversationHandler.END

    ctx.user_data["pay_order_id"] = order_id
    await q.edit_message_text(ASK_PROOF, parse_mode="Markdown")
    return STEP_PAY_PROOF


async def receive_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """استلام صورة إثبات الدفع"""
    msg      = update.message
    user     = update.effective_user
    order_id = ctx.user_data.get("pay_order_id")

    if not order_id:
        return ConversationHandler.END

    file_id = _extract_photo(msg)
    if not file_id:
        await msg.reply_text(NOT_PHOTO, parse_mode="Markdown")
        return STEP_PAY_PROOF

    order = await get_order(order_id)
    if not order:
        await msg.reply_text("⚠️ الطلب غير موجود.")
        return ConversationHandler.END

    # تسجيل الإثبات → حالة PAYMENT_SENT (Protected)
    await set_payment_proof(order_id, file_id)

    # تأكيد للمستخدم
    await msg.reply_text(
        PROOF_RECEIVED.format(order_id=order_id),
        parse_mode   = "Markdown",
        reply_markup = kb_main(),
    )

    # إشعار الأدمن — صورة إثبات الدفع + أزرار الموافقة المحمية
    caption = ADMIN_PROOF_RECEIVED.format(
        order_id  = order["id"],
        full_name = order.get("full_name") or order.get("username") or "مجهول",
        user_id   = order["user_id"],
        game_emoji= "",
        game_name = order["game_name"],
        package_label = order["package_label"],
        player_id = order["player_id"],
        amount    = order["amount"],
        currency  = order["currency"],
        time      = now_str(),
    )
    try:
        await ctx.bot.send_photo(
            chat_id      = ADMIN_ID,
            photo        = file_id,
            caption      = caption,
            parse_mode   = "Markdown",
            reply_markup = kb_admin_proof(order_id),
        )
    except Exception as e:
        log.error(f"[Proof notify admin] {e}")

    # تنظيف
    ctx.user_data.pop("pay_order_id", None)
    ctx.bot_data.get("user_pending_payment", {}).pop(user.id, None)
    return ConversationHandler.END
