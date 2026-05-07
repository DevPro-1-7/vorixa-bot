"""
CharglyBot V3 — تقديم الطلب (4 خطوات)

Game → Player ID → Player Name → Screenshot → Package
↓
إنشاء الطلب → إشعار الأدمن بالصورة + البيانات
"""
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from core.config  import ADMIN_ID, RATE_LIMIT_SECONDS
from core.states  import (STEP_GAME, STEP_PLAYER_ID, STEP_PLAYER_NAME,
                           STEP_SCREENSHOT, STEP_PACKAGE)
from database     import (is_banned, check_rate_limit, touch_last_action,
                           count_active_orders, get_active_games, get_packages,
                           get_package, get_game, create_order)
from handlers.keyboards import (kb_games, kb_packages, kb_cancel,
                                  kb_main, kb_admin_review)
from handlers.messages  import (
    STEP_GAME as MSG_GAME, STEP_PLAYER_ID as MSG_PID,
    STEP_PLAYER_NAME as MSG_PNAME, STEP_SCREENSHOT as MSG_SHOT,
    STEP_PACKAGE as MSG_PKG, ORDER_SUBMITTED,
    ADMIN_NEW_ORDER, CANCELLED, RATE_LIMIT, BANNED,
    BAD_ID, BAD_NAME, NOT_PHOTO, ACTIVE_ORDER, now_str,
)

log = logging.getLogger(__name__)


# ── Entry ────────────────────────────────────────

async def charge_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    u = update.effective_user

    if await is_banned(u.id):
        await update.message.reply_text(BANNED)
        return ConversationHandler.END

    if not await check_rate_limit(u.id, RATE_LIMIT_SECONDS):
        await update.message.reply_text(RATE_LIMIT)
        return ConversationHandler.END

    if await count_active_orders(u.id) >= 1:
        await update.message.reply_text(ACTIVE_ORDER, parse_mode="Markdown")
        return ConversationHandler.END

    await touch_last_action(u.id)
    ctx.user_data.clear()

    games = await get_active_games()
    if not games:
        await update.message.reply_text(
            "⚠️ لا توجد ألعاب متاحة حالياً. حاول لاحقاً.")
        return ConversationHandler.END

    await update.message.reply_text(
        MSG_GAME, parse_mode="Markdown", reply_markup=kb_games(games)
    )
    return STEP_GAME


# ── خطوة 1: اختيار اللعبة ───────────────────────

async def cb_select_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    game_key = q.data.split(":", 1)[1]
    game = await get_game(game_key)
    if not game or not game["is_active"]:
        await q.edit_message_text("⚠️ هذه اللعبة غير متاحة.")
        return ConversationHandler.END

    ctx.user_data["game_key"]   = game_key
    ctx.user_data["game_name"]  = game["name"]
    ctx.user_data["game_emoji"] = game["emoji"]

    await q.edit_message_text(
        MSG_PID.format(game_name=game["name"]),
        parse_mode="Markdown",
    )
    return STEP_PLAYER_ID


async def cb_back_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    games = await get_active_games()
    await q.edit_message_text(
        MSG_GAME, parse_mode="Markdown", reply_markup=kb_games(games)
    )
    return STEP_GAME


# ── خطوة 2: Player ID ───────────────────────────

async def receive_player_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    pid = update.message.text.strip()
    if not pid.isdigit() or not (6 <= len(pid) <= 12):
        await update.message.reply_text(BAD_ID)
        return STEP_PLAYER_ID

    ctx.user_data["player_id"] = pid
    await update.message.reply_text(
        MSG_PNAME.format(player_id=pid), parse_mode="Markdown"
    )
    return STEP_PLAYER_NAME


# ── خطوة 3: اسم اللاعب ──────────────────────────

async def receive_player_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 24:
        await update.message.reply_text(BAD_NAME)
        return STEP_PLAYER_NAME

    ctx.user_data["player_name"] = name
    await update.message.reply_text(
        MSG_SHOT.format(player_name=name), parse_mode="Markdown"
    )
    return STEP_SCREENSHOT


# ── خطوة 4: صورة البروفايل ──────────────────────

async def receive_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    file_id = _extract_photo(msg)
    if not file_id:
        await msg.reply_text(NOT_PHOTO, parse_mode="Markdown")
        return STEP_SCREENSHOT

    ctx.user_data["screenshot_file_id"] = file_id
    game_key = ctx.user_data["game_key"]
    pkgs = await get_packages(game_key)
    if not pkgs:
        await msg.reply_text("⚠️ لا توجد باقات متاحة لهذه اللعبة.")
        return ConversationHandler.END

    await msg.reply_text(
        MSG_PKG, parse_mode="Markdown", reply_markup=kb_packages(pkgs)
    )
    return STEP_PACKAGE


# ── خطوة 5: اختيار الباقة + إنشاء الطلب ────────

async def cb_pick_package(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    pkg_id = int(q.data.split(":", 1)[1])
    pkg    = await get_package(pkg_id)
    if not pkg:
        await q.edit_message_text("⚠️ الباقة غير موجودة.")
        return ConversationHandler.END

    u          = update.effective_user
    player_id  = ctx.user_data.get("player_id")
    player_name= ctx.user_data.get("player_name")
    screenshot = ctx.user_data.get("screenshot_file_id")
    game_key   = ctx.user_data.get("game_key")
    game_name  = ctx.user_data.get("game_name")
    game_emoji = ctx.user_data.get("game_emoji", "🎮")

    if not all([player_id, player_name, screenshot, game_key]):
        await q.edit_message_text("⚠️ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    profit = pkg["amount"] - pkg["cost"]

    order_id = await create_order(
        user_id         = u.id,
        game_key        = game_key,
        game_name       = game_name,
        player_id       = player_id,
        player_name     = player_name,
        screenshot_file_id = screenshot,
        package_id      = pkg_id,
        package_label   = pkg["label"],
        amount          = pkg["amount"],
        cost            = pkg["cost"],
        currency        = pkg["currency"],
    )

    # تأكيد للمستخدم
    await q.edit_message_text(
        ORDER_SUBMITTED.format(
            order_id      = order_id,
            game_emoji    = game_emoji,
            game_name     = game_name,
            player_id     = player_id,
            player_name   = player_name,
            package_label = pkg["label"],
            amount        = pkg["amount"],
            currency      = pkg["currency"],
            time          = now_str(),
        ),
        parse_mode="Markdown",
    )

    # إشعار الأدمن — صورة + بيانات + أزرار
    caption = ADMIN_NEW_ORDER.format(
        order_id      = order_id,
        full_name     = u.full_name or u.username or "مجهول",
        user_id       = u.id,
        game_emoji    = game_emoji,
        game_name     = game_name,
        player_id     = player_id,
        player_name   = player_name,
        package_label = pkg["label"],
        amount        = pkg["amount"],
        currency      = pkg["currency"],
        profit        = profit,
        time          = now_str(),
    )
    try:
        await ctx.bot.send_photo(
            chat_id      = ADMIN_ID,
            photo        = screenshot,
            caption      = caption,
            parse_mode   = "Markdown",
            reply_markup = kb_admin_review(order_id),
        )
    except Exception as e:
        log.error(f"[Admin notify] {e}")

    ctx.user_data.clear()
    return ConversationHandler.END


# ── إلغاء ─────────────────────────────────────────

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(CANCELLED)
    else:
        await update.message.reply_text(CANCELLED, reply_markup=kb_main())
    return ConversationHandler.END


# ── مساعد ─────────────────────────────────────────

def _extract_photo(msg) -> str | None:
    if msg.photo:
        return msg.photo[-1].file_id
    if msg.document and msg.document.mime_type and "image" in msg.document.mime_type:
        return msg.document.file_id
    return None
