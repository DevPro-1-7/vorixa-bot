"""
CharglyBot V3 — diigiure project
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pre-Approval Digital Commerce System
شغّل: python main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import asyncio
import logging

from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
)

from core         import BOT_TOKEN, ADMIN_ID
from core.states  import (
    STEP_GAME, STEP_PLAYER_ID, STEP_PLAYER_NAME,
    STEP_SCREENSHOT, STEP_PACKAGE,
    STEP_EDIT_MENU, STEP_EDIT_FIELD,
    STEP_PAY_PROOF,
)
from database     import init_db
from jobs         import expire_orders_job
from handlers     import (
    # user
    cmd_start, btn_support, btn_my_orders, fallback_unknown,
    # charge
    charge_entry, cb_select_game, cb_back_game,
    receive_player_id, receive_player_name,
    receive_screenshot, cb_pick_package, cancel,
    # edit
    edit_entry, cb_edit_menu, cb_edit_dispatch,
    receive_edit_value, cb_edit_pick_package,
    cb_edit_pick_game, cb_cancel_order, cancel_edit,
    # payment
    cb_pay_proof, receive_proof,
    # admin
    cmd_admin, admin_callback, admin_text,
)

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s │ %(levelname)-8s │ %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

MEDIA = filters.PHOTO | filters.Document.ALL


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # ══════════════════════════════════════════════
    #  Conversation 1: تقديم الطلب
    # ══════════════════════════════════════════════
    order_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🎮 شحن الآن$"), charge_entry)
        ],
        states={
            STEP_GAME: [
                CallbackQueryHandler(cb_select_game, pattern="^game:"),
                CallbackQueryHandler(cancel,         pattern="^cancel$"),
            ],
            STEP_PLAYER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_player_id)
            ],
            STEP_PLAYER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_player_name)
            ],
            STEP_SCREENSHOT: [
                MessageHandler(MEDIA | (filters.TEXT & ~filters.COMMAND), receive_screenshot)
            ],
            STEP_PACKAGE: [
                CallbackQueryHandler(cb_pick_package, pattern="^pkg:"),
                CallbackQueryHandler(cb_back_game,    pattern="^back_game$"),
                CallbackQueryHandler(cancel,           pattern="^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("start",  cmd_start),
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        allow_reentry=True,
        name="order_conv",
    )

    # ══════════════════════════════════════════════
    #  Conversation 2: تعديل الطلب
    # ══════════════════════════════════════════════
    edit_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^✏️ تعديل طلبي$"), edit_entry),
            CallbackQueryHandler(cb_edit_menu, pattern="^edit:menu:"),
        ],
        states={
            STEP_EDIT_MENU: [
                CallbackQueryHandler(cb_edit_dispatch, pattern="^edit:"),
            ],
            STEP_EDIT_FIELD: [
                MessageHandler(
                    (filters.TEXT & ~filters.COMMAND) | MEDIA,
                    receive_edit_value
                ),
            ],
            # تغيير اللعبة أو الباقة ضمن التعديل
            STEP_GAME: [
                CallbackQueryHandler(cb_edit_pick_game, pattern="^game:"),
            ],
            STEP_PACKAGE: [
                CallbackQueryHandler(cb_edit_pick_package, pattern="^pkg:"),
                CallbackQueryHandler(cb_edit_dispatch,     pattern="^edit:"),
            ],
        },
        fallbacks=[
            CommandHandler("start",  cmd_start),
            CommandHandler("cancel", cancel_edit),
            CallbackQueryHandler(cancel_edit, pattern="^cancel$"),
        ],
        allow_reentry=True,
        name="edit_conv",
    )

    # ══════════════════════════════════════════════
    #  Conversation 3: إثبات الدفع
    # ══════════════════════════════════════════════
    payment_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_pay_proof, pattern="^pay:proof$"),
        ],
        states={
            STEP_PAY_PROOF: [
                MessageHandler(MEDIA | (filters.TEXT & ~filters.COMMAND), receive_proof)
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
        ],
        allow_reentry=True,
        name="payment_conv",
    )

    # ══════════════════════════════════════════════
    #  تسجيل جميع الـ Handlers
    # ══════════════════════════════════════════════

    # أوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))

    # المحادثات
    app.add_handler(order_conv)
    app.add_handler(edit_conv)
    app.add_handler(payment_conv)

    # أزرار القائمة الرئيسية
    app.add_handler(MessageHandler(filters.Regex("^📦 طلباتي$"),    btn_my_orders))
    app.add_handler(MessageHandler(filters.Regex("^📞 الدعم$"),      btn_support))

    # Callbacks الأدمن
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm:"))

    # إلغاء الطلب من callback
    app.add_handler(CallbackQueryHandler(cb_cancel_order, pattern="^order:cancel:"))

    # رسائل نصية الأدمن (reject reason, flows, broadcast)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
            admin_text,
        )
    )

    # أي رسالة غير معروفة
    app.add_handler(MessageHandler(filters.ALL, fallback_unknown))

    # مهمة انتهاء مهلة الدفع
    app.job_queue.run_repeating(expire_orders_job, interval=60, first=15)

    return app


async def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.error("❌  BOT_TOKEN غير محدد في .env")
        return
    if not ADMIN_ID:
        log.error("❌  ADMIN_ID غير محدد في .env")
        return

    log.info("🗄️  تهيئة قاعدة البيانات...")
    await init_db()

    app = build_app()

    log.info("🚀  CharglyBot V3 — diigiure project")
    log.info(f"👑  Admin ID : {ADMIN_ID}")
    log.info("✅  البوت يعمل — Ctrl+C للإيقاف\n")

    async with app:
        await app.start()
        await app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑  تم الإيقاف.")
