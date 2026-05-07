"""
CharglyBot V3 — مهمة انتهاء مهلة الدفع
تعمل كل دقيقة
"""
import logging
from telegram.ext import ContextTypes
from database import get_expired_orders, set_order_status
from core.states import S
from handlers.messages import ORDER_EXPIRED
from core.config import PAYMENT_TIMEOUT_MINUTES

log = logging.getLogger(__name__)


async def expire_orders_job(ctx: ContextTypes.DEFAULT_TYPE):
    expired = await get_expired_orders()
    for order in expired:
        await set_order_status(order["id"], S.EXPIRED, actor="system:expiry")
        log.info(f"[Expiry] Order #{order['id']} expired")
        try:
            await ctx.bot.send_message(
                chat_id    = order["user_id"],
                text       = ORDER_EXPIRED.format(
                    order_id = order["id"],
                    timeout  = PAYMENT_TIMEOUT_MINUTES,
                ),
                parse_mode = "Markdown",
            )
        except Exception as e:
            log.warning(f"[Expiry notify] {e}")
