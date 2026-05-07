"""
CharglyBot V3 — تعديل الطلب قبل موافقة الأدمن

العميل يستطيع تعديل:
  - Player ID
  - اسم اللاعب
  - اللعبة (يُعيد اختيار الباقة)
  - الباقة
  - الصورة
  - إلغاء الطلب

🔒 يُقفل تلقائياً بعد موافقة الأدمن.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from core.states  import STEP_EDIT_MENU, STEP_EDIT_FIELD, STEP_GAME, STEP_PACKAGE
from database     import (get_user_active_order, update_order_field, cancel_order,
                           get_active_games, get_packages, get_package, get_game,
                           get_order)
from core.states  import S
from handlers.keyboards import (kb_edit_menu, kb_main, kb_games, kb_packages)
from handlers.messages  import (
    EDIT_MENU, EDIT_ASK_PID, EDIT_ASK_NAME, EDIT_ASK_PHOTO,
    EDIT_DONE, EDIT_LOCKED, EDIT_NO_ORDER, BAD_ID, BAD_NAME, NOT_PHOTO,
    ORDER_CANCELLED_USER, ORDER_CANCEL_LOCKED,
)
from handlers.charge import _extract_photo

log = logging.getLogger(__name__)


# ── Entry: زر "تعديل طلبي" ──────────────────────

async def edit_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    order = await get_user_active_order(update.effective_user.id)

    if not order:
        await update.message.reply_text(EDIT_NO_ORDER, parse_mode="Markdown")
        return ConversationHandler.END

    if order["status"] not in S.EDITABLE:
        await update.message.reply_text(EDIT_LOCKED, parse_mode="Markdown")
        return ConversationHandler.END

    ctx.user_data["edit_order_id"] = order["id"]
    await update.message.reply_text(
        EDIT_MENU.format(
            order_id      = order["id"],
            game_emoji    = "",
            game_name     = order["game_name"],
            package_label = order["package_label"],
            player_id     = order["player_id"],
            player_name   = order["player_name"],
        ),
        parse_mode   = "Markdown",
        reply_markup = kb_edit_menu(order["id"]),
    )
    return STEP_EDIT_MENU


# ── Entry via callback: edit:menu:ID ────────────

async def cb_edit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    order_id = int(q.data.split(":")[2])
    order    = await get_order(order_id)

    if not order or order["status"] not in S.EDITABLE:
        await q.edit_message_text(EDIT_LOCKED)
        return ConversationHandler.END

    ctx.user_data["edit_order_id"] = order_id
    await q.edit_message_text(
        EDIT_MENU.format(
            order_id      = order["id"],
            game_emoji    = "",
            game_name     = order["game_name"],
            package_label = order["package_label"],
            player_id     = order["player_id"],
            player_name   = order["player_name"],
        ),
        parse_mode   = "Markdown",
        reply_markup = kb_edit_menu(order_id),
    )
    return STEP_EDIT_MENU


# ── Callbacks من قائمة التعديل ──────────────────

async def cb_edit_dispatch(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """
    edit:pid:ID    → تعديل Player ID
    edit:name:ID   → تعديل الاسم
    edit:photo:ID  → إعادة رفع الصورة
    edit:game:ID   → تغيير اللعبة
    edit:package:ID→ تغيير الباقة
    edit:back:ID   → رجوع
    """
    q      = update.callback_query
    await q.answer()
    parts  = q.data.split(":")
    action = parts[1]
    order_id = int(parts[2])

    # تحقق من إمكانية التعديل
    order = await get_order(order_id)
    if not order or order["status"] not in S.EDITABLE:
        await q.edit_message_text(EDIT_LOCKED)
        return ConversationHandler.END

    ctx.user_data["edit_order_id"]  = order_id
    ctx.user_data["edit_action"]    = action

    if action == "pid":
        await q.edit_message_text(EDIT_ASK_PID, parse_mode="Markdown")
        return STEP_EDIT_FIELD

    if action == "name":
        await q.edit_message_text(EDIT_ASK_NAME, parse_mode="Markdown")
        return STEP_EDIT_FIELD

    if action == "photo":
        await q.edit_message_text(EDIT_ASK_PHOTO, parse_mode="Markdown")
        return STEP_EDIT_FIELD

    if action == "game":
        games = await get_active_games()
        await q.edit_message_text(
            "🎮 *اختر اللعبة الجديدة:*",
            parse_mode   = "Markdown",
            reply_markup = kb_games(games),
        )
        return STEP_GAME

    if action == "package":
        pkgs = await get_packages(order["game_key"])
        await q.edit_message_text(
            "📦 *اختر الباقة الجديدة:*",
            parse_mode   = "Markdown",
            reply_markup = kb_packages(pkgs),
        )
        return STEP_PACKAGE

    if action == "back":
        await q.edit_message_text("تم. استخدم الأزرار أدناه 👇")
        return ConversationHandler.END

    return STEP_EDIT_MENU


# ── استلام القيمة الجديدة (نص أو صورة) ─────────

async def receive_edit_value(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    action   = ctx.user_data.get("edit_action")
    order_id = ctx.user_data.get("edit_order_id")

    if not order_id or not action:
        return ConversationHandler.END

    msg = update.message

    if action == "pid":
        val = msg.text.strip() if msg.text else ""
        if not val.isdigit() or not (6 <= len(val) <= 12):
            await msg.reply_text(BAD_ID)
            return STEP_EDIT_FIELD
        ok = await update_order_field(order_id, "player_id", val, f"user:{update.effective_user.id}")

    elif action == "name":
        val = msg.text.strip() if msg.text else ""
        if len(val) < 2 or len(val) > 24:
            await msg.reply_text(BAD_NAME)
            return STEP_EDIT_FIELD
        ok = await update_order_field(order_id, "player_name", val, f"user:{update.effective_user.id}")

    elif action == "photo":
        file_id = _extract_photo(msg)
        if not file_id:
            await msg.reply_text(NOT_PHOTO, parse_mode="Markdown")
            return STEP_EDIT_FIELD
        ok = await update_order_field(order_id, "screenshot_file_id", file_id, f"user:{update.effective_user.id}")

    else:
        ok = False

    if ok:
        await msg.reply_text(EDIT_DONE, reply_markup=kb_main())
    else:
        await msg.reply_text(EDIT_LOCKED, reply_markup=kb_main())

    ctx.user_data.pop("edit_action", None)
    ctx.user_data.pop("edit_order_id", None)
    return ConversationHandler.END


# ── تعديل الباقة عبر callback ───────────────────

async def cb_edit_pick_package(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q      = update.callback_query
    await q.answer()
    pkg_id   = int(q.data.split(":", 1)[1])
    order_id = ctx.user_data.get("edit_order_id")

    pkg   = await get_package(pkg_id)
    order = await get_order(order_id) if order_id else None

    if not pkg or not order or order["status"] not in S.EDITABLE:
        await q.edit_message_text(EDIT_LOCKED)
        return ConversationHandler.END

    await update_order_field(order_id, "package_id",    str(pkg_id),     f"user:{update.effective_user.id}")
    await update_order_field(order_id, "package_label", pkg["label"],    f"user:{update.effective_user.id}")
    await update_order_field(order_id, "amount",        str(pkg["amount"]), f"user:{update.effective_user.id}")
    await update_order_field(order_id, "cost",          str(pkg["cost"]), f"user:{update.effective_user.id}")

    await q.edit_message_text(
        f"{EDIT_DONE}\n📦 الباقة الجديدة: *{pkg['label']}*",
        parse_mode="Markdown",
    )
    ctx.user_data.pop("edit_order_id", None)
    return ConversationHandler.END


# ── تعديل اللعبة عبر callback ───────────────────

async def cb_edit_pick_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q        = update.callback_query
    await q.answer()
    game_key = q.data.split(":", 1)[1]
    order_id = ctx.user_data.get("edit_order_id")
    game     = await get_game(game_key)
    order    = await get_order(order_id) if order_id else None

    if not game or not order or order["status"] not in S.EDITABLE:
        await q.edit_message_text(EDIT_LOCKED)
        return ConversationHandler.END

    await update_order_field(order_id, "game_key",  game_key,     f"user:{update.effective_user.id}")
    await update_order_field(order_id, "game_name", game["name"], f"user:{update.effective_user.id}")

    # اختيار الباقة من اللعبة الجديدة
    ctx.user_data["edit_action"] = "package"
    pkgs = await get_packages(game_key)
    await q.edit_message_text(
        f"✅ اللعبة: *{game['name']}*\n\n📦 *اختر الباقة:*",
        parse_mode   = "Markdown",
        reply_markup = kb_packages(pkgs),
    )
    return STEP_PACKAGE


# ── إلغاء الطلب ──────────────────────────────────

async def cb_cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q        = update.callback_query
    await q.answer()
    order_id = int(q.data.split(":")[2])
    user_id  = update.effective_user.id

    ok = await cancel_order(order_id, user_id)
    if ok:
        await q.edit_message_text(
            ORDER_CANCELLED_USER.format(order_id=order_id),
            parse_mode="Markdown",
        )
    else:
        await q.edit_message_text(ORDER_CANCEL_LOCKED, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_edit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.pop("edit_action",   None)
    ctx.user_data.pop("edit_order_id", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("تم إلغاء التعديل.")
    else:
        await update.message.reply_text("تم إلغاء التعديل.", reply_markup=kb_main())
    return ConversationHandler.END
