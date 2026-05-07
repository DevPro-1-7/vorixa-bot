"""
CharglyBot V3 — لوحة تحكم الأدمن الكاملة

الأوامر:
  /admin          → لوحة التحكم
  adm:approve     → قبول طلب
  adm:reject      → رفض طلب (مع سبب)
  adm:complete    → تأكيد الشحن
  adm:processing  → وضع قيد التنفيذ
  adm:issue       → مشكلة في التحويل
  adm:list        → قائمة الطلبات
  adm:stats       → الإحصائيات
  adm:games       → إدارة الألعاب
  adm:g:*         → عمليات الألعاب
  adm:p:*         → عمليات الباقات
  adm:broadcast   → إشعار جماعي
"""
import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from core.config  import ADMIN_ID, SUPPORT_LINK, PAYMENT_NUMBER, PAYMENT_NAME, PAYMENT_TIMEOUT_MINUTES
from core.states  import S, ADMIN_ADD_GAME, ADMIN_ADD_PKG, ADMIN_EDIT_PRICE, ADMIN_BROADCAST, ADMIN_SET_COST
from database     import (
    get_order, set_order_status, approve_order,
    get_all_orders, daily_stats,
    get_all_games, get_all_packages, add_game, toggle_game, delete_game,
    add_package, update_package_price, toggle_package, delete_package,
    get_all_user_ids,
)
from handlers.keyboards import (
    kb_admin_panel, kb_admin_review, kb_admin_proof,
    kb_admin_processing, kb_admin_games, kb_admin_packages, kb_admin_back,
    kb_pay_action,
)
from handlers.messages import (
    ADMIN_STATS, ADMIN_APPROVED_OK, ADMIN_COMPLETED_OK,
    ADMIN_PROCESSING_OK, ADMIN_REJECTED_OK, ADMIN_ALREADY_DONE,
    ADMIN_PROTECTED, ADMIN_ASK_REASON, ADMIN_ASK_ISSUE,
    ADMIN_ASK_GAME_KEY, ADMIN_ASK_GAME_NAME, ADMIN_ASK_GAME_EMOJI,
    ADMIN_GAME_ADDED, ADMIN_GAME_TOGGLED, ADMIN_GAME_DELETED,
    ADMIN_ASK_PKG_LABEL, ADMIN_ASK_PKG_PRICE, ADMIN_ASK_PKG_COST,
    ADMIN_PKG_ADDED, ADMIN_PKG_TOGGLED, ADMIN_PKG_DELETED,
    ADMIN_ASK_NEW_PRICE, ADMIN_ASK_NEW_COST, ADMIN_PKG_UPDATED,
    ADMIN_ASK_BROADCAST, ADMIN_BROADCAST_DONE,
    ORDER_COMPLETED, ORDER_REJECTED, ORDER_PROCESSING, ORDER_ISSUE,
    fmt_order_row, fmt_payment_msg, now_str,
)

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════
#  Decorator
# ══════════════════════════════════════════════════

def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid != ADMIN_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ غير مصرح.", show_alert=True)
            else:
                await update.message.reply_text("⛔ غير مصرح.")
            return
        return await fn(update, ctx)
    return wrapper


# ══════════════════════════════════════════════════
#  /admin — لوحة التحكم
# ══════════════════════════════════════════════════

@admin_only
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = await daily_stats()
    text = (
        f"👑 *CharglyBot V3 — لوحة التحكم*\n\n"
        f"🔍 مراجعة: *{stats['pending']}*   "
        f"💳 إثبات دفع: *{stats['waiting']}*\n"
        f"⚡ تنفيذ: *{stats['processing']}*   "
        f"✅ مكتمل: *{stats['completed']}*\n"
        f"💰 أرباح اليوم: *{stats['revenue']:.0f} دج*   "
        f"📈 صافي: *{stats['profit']:.0f} دج*\n\n"
        f"اختر إجراءً 👇"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=kb_admin_panel()
    )


# ══════════════════════════════════════════════════
#  معالج Callbacks الأدمن الموحّد
# ══════════════════════════════════════════════════

@admin_only
async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q     = update.callback_query
    await q.answer()
    data  = q.data   # adm:action:param
    parts = data.split(":")

    action = parts[1] if len(parts) > 1 else ""

    # ────────────────────────────────────────────
    #  لوحة التحكم الرئيسية
    # ────────────────────────────────────────────
    if action == "panel":
        stats = await daily_stats()
        text  = (
            f"👑 *CharglyBot V3 — لوحة التحكم*\n\n"
            f"🔍 مراجعة: *{stats['pending']}*   "
            f"💳 إثبات دفع: *{stats['waiting']}*\n"
            f"⚡ تنفيذ: *{stats['processing']}*   "
            f"✅ مكتمل: *{stats['completed']}*\n"
            f"💰 *{stats['revenue']:.0f} دج*   صافي: *{stats['profit']:.0f} دج*\n\n"
            f"اختر إجراءً 👇"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_admin_panel())
        return

    # ────────────────────────────────────────────
    #  الإحصائيات
    # ────────────────────────────────────────────
    if action == "stats":
        stats = await daily_stats()
        await q.edit_message_text(
            ADMIN_STATS.format(**stats),
            parse_mode   = "Markdown",
            reply_markup = kb_admin_panel(),
        )
        return

    # ────────────────────────────────────────────
    #  قائمة الطلبات
    # ────────────────────────────────────────────
    if action == "list":
        status_filter = parts[2] if len(parts) > 2 and parts[2] != "all" else None
        orders = await get_all_orders(status=status_filter, limit=15)
        header = f"📋 *الطلبات — {status_filter or 'الكل'} ({len(orders)})*\n\n"
        if not orders:
            await q.edit_message_text("📭 لا توجد طلبات.", reply_markup=kb_admin_panel())
            return
        await q.edit_message_text(header, parse_mode="Markdown", reply_markup=kb_admin_panel())
        for o in orders:
            kb = None
            if o["status"] == "awaiting_approval":
                kb = kb_admin_review(o["id"])
            elif o["status"] == "payment_sent":
                kb = kb_admin_proof(o["id"])
            elif o["status"] == "processing":
                kb = kb_admin_processing(o["id"])
            await q.message.reply_text(
                fmt_order_row(o), parse_mode="Markdown", reply_markup=kb
            )
        return

    # ────────────────────────────────────────────
    #  موافقة على الطلب
    # ────────────────────────────────────────────
    if action == "approve":
        order_id = int(parts[2])
        order    = await get_order(order_id)
        if not order:
            await q.edit_message_text("⚠️ الطلب غير موجود.")
            return
        if order["status"] != "awaiting_approval":
            await q.answer(ADMIN_ALREADY_DONE, show_alert=True)
            return

        await approve_order(order_id)

        # تحديث رسالة الأدمن
        new_caption = (q.message.caption or "") + \
            f"\n\n✅ *تمت الموافقة — {now_str()}*"
        try:
            await q.edit_message_caption(
                caption=new_caption, parse_mode="Markdown"
            )
        except Exception:
            pass

        # إرسال تفاصيل الدفع للمستخدم
        order = await get_order(order_id)
        pay_msg = fmt_payment_msg(order)
        try:
            await ctx.bot.send_message(
                chat_id      = order["user_id"],
                text         = pay_msg,
                parse_mode   = "Markdown",
                reply_markup = kb_pay_action(),
            )
        except Exception as e:
            log.error(f"[Send payment] {e}")

        # حفظ order_id لمعالج الدفع
        ctx.bot_data.setdefault("user_pending_payment", {})[order["user_id"]] = order_id
        return

    # ────────────────────────────────────────────
    #  تأكيد الشحن
    # ────────────────────────────────────────────
    if action == "complete":
        order_id = int(parts[2])
        order    = await get_order(order_id)
        if not order:
            await q.edit_message_text("⚠️ الطلب غير موجود.")
            return
        if order["status"] in S.TERMINAL:
            await q.answer(ADMIN_ALREADY_DONE, show_alert=True)
            return

        await set_order_status(order_id, S.COMPLETED, actor="admin")
        try:
            await q.edit_message_caption(
                caption=(q.message.caption or "") + f"\n\n🎉 *تم الشحن — {now_str()}*",
                parse_mode="Markdown",
            )
        except Exception:
            pass

        try:
            await ctx.bot.send_message(
                chat_id    = order["user_id"],
                text       = ORDER_COMPLETED.format(
                    order_id      = order["id"],
                    game_emoji    = "",
                    game_name     = order["game_name"],
                    package_label = order["package_label"],
                    player_id     = order["player_id"],
                ),
                parse_mode = "Markdown",
            )
        except Exception as e:
            log.warning(f"[Notify complete] {e}")
        return

    # ────────────────────────────────────────────
    #  قيد التنفيذ
    # ────────────────────────────────────────────
    if action == "processing":
        order_id = int(parts[2])
        order    = await get_order(order_id)
        if not order or order["status"] in S.TERMINAL:
            await q.answer(ADMIN_ALREADY_DONE, show_alert=True)
            return

        await set_order_status(order_id, S.PROCESSING, actor="admin")
        try:
            await q.edit_message_caption(
                caption=(q.message.caption or "") + f"\n\n⚡ *قيد التنفيذ — {now_str()}*",
                parse_mode="Markdown",
                reply_markup=kb_admin_processing(order_id),
            )
        except Exception:
            pass

        try:
            await ctx.bot.send_message(
                chat_id    = order["user_id"],
                text       = ORDER_PROCESSING.format(
                    order_id      = order["id"],
                    game_emoji    = "",
                    game_name     = order["game_name"],
                    package_label = order["package_label"],
                ),
                parse_mode = "Markdown",
            )
        except Exception as e:
            log.warning(f"[Notify processing] {e}")
        return

    # ────────────────────────────────────────────
    #  مشكلة في التحويل
    # ────────────────────────────────────────────
    if action == "issue":
        order_id = int(parts[2])
        ctx.user_data["issue_order_id"] = order_id
        await ctx.bot.send_message(
            chat_id    = ADMIN_ID,
            text       = ADMIN_ASK_ISSUE,
            parse_mode = "Markdown",
        )
        return

    # ────────────────────────────────────────────
    #  رفض الطلب
    # ────────────────────────────────────────────
    if action == "reject":
        order_id = int(parts[2])
        order    = await get_order(order_id)
        if not order:
            await q.edit_message_text("⚠️ الطلب غير موجود.")
            return
        if order["status"] in S.PROTECTED:
            await q.answer(ADMIN_PROTECTED, show_alert=True)
            return
        if order["status"] in S.TERMINAL:
            await q.answer(ADMIN_ALREADY_DONE, show_alert=True)
            return

        ctx.user_data["reject_order_id"] = order_id
        await ctx.bot.send_message(
            chat_id    = ADMIN_ID,
            text       = ADMIN_ASK_REASON,
            parse_mode = "Markdown",
        )
        return

    # ────────────────────────────────────────────
    #  إدارة الألعاب
    # ────────────────────────────────────────────
    if action == "games":
        games = await get_all_games()
        await q.edit_message_text(
            "🎮 *إدارة الألعاب*\n\n✅ = نشطة  |  ⏸️ = متوقفة",
            parse_mode   = "Markdown",
            reply_markup = kb_admin_games(games),
        )
        return

    if action == "g":
        sub = parts[2]

        if sub == "add":
            ctx.user_data["admin_flow"] = "add_game_key"
            await q.edit_message_text(ADMIN_ASK_GAME_KEY, parse_mode="Markdown")
            return

        if sub == "toggle":
            game_key = parts[3]
            from database import get_game
            game = await get_game(game_key)
            await toggle_game(game_key)
            await q.answer(ADMIN_GAME_TOGGLED.format(name=game["name"] if game else game_key))
            games = await get_all_games()
            await q.edit_message_text(
                "🎮 *إدارة الألعاب*",
                parse_mode   = "Markdown",
                reply_markup = kb_admin_games(games),
            )
            return

        if sub == "delete":
            game_key = parts[3]
            from database import get_game
            game = await get_game(game_key)
            await delete_game(game_key)
            await q.answer(ADMIN_GAME_DELETED.format(name=game["name"] if game else game_key))
            games = await get_all_games()
            await q.edit_message_text(
                "🎮 *إدارة الألعاب*",
                parse_mode   = "Markdown",
                reply_markup = kb_admin_games(games),
            )
            return

        if sub == "pkgs":
            game_key = parts[3]
            from database import get_game
            game = await get_game(game_key)
            pkgs = await get_all_packages(game_key)
            await q.edit_message_text(
                f"📦 *باقات {game['name'] if game else game_key}*",
                parse_mode   = "Markdown",
                reply_markup = kb_admin_packages(pkgs, game_key),
            )
            return

    # ────────────────────────────────────────────
    #  إدارة الباقات
    # ────────────────────────────────────────────
    if action == "p":
        sub = parts[2]

        if sub == "add":
            game_key = parts[3]
            ctx.user_data["admin_flow"]    = "add_pkg_label"
            ctx.user_data["admin_game_key"]= game_key
            await q.edit_message_text(ADMIN_ASK_PKG_LABEL, parse_mode="Markdown")
            return

        if sub == "toggle":
            pkg_id   = int(parts[3])
            game_key = parts[4]
            await toggle_package(pkg_id)
            await q.answer(ADMIN_PKG_TOGGLED)
            pkgs = await get_all_packages(game_key)
            from database import get_game
            game = await get_game(game_key)
            await q.edit_message_text(
                f"📦 *باقات {game['name'] if game else game_key}*",
                parse_mode   = "Markdown",
                reply_markup = kb_admin_packages(pkgs, game_key),
            )
            return

        if sub == "delete":
            pkg_id   = int(parts[3])
            game_key = parts[4]
            await delete_package(pkg_id)
            await q.answer(ADMIN_PKG_DELETED)
            pkgs = await get_all_packages(game_key)
            from database import get_game
            game = await get_game(game_key)
            await q.edit_message_text(
                f"📦 *باقات {game['name'] if game else game_key}*",
                parse_mode   = "Markdown",
                reply_markup = kb_admin_packages(pkgs, game_key),
            )
            return

        if sub == "edit":
            pkg_id = int(parts[3])
            ctx.user_data["admin_flow"]   = "edit_pkg_price"
            ctx.user_data["admin_pkg_id"] = pkg_id
            await q.edit_message_text(ADMIN_ASK_NEW_PRICE, parse_mode="Markdown")
            return

    # ────────────────────────────────────────────
    #  إشعار جماعي
    # ────────────────────────────────────────────
    if action == "broadcast":
        ctx.user_data["admin_flow"] = "broadcast"
        await q.edit_message_text(ADMIN_ASK_BROADCAST, parse_mode="Markdown")
        return


# ══════════════════════════════════════════════════
#  معالج رسائل الأدمن النصية (flows)
# ══════════════════════════════════════════════════

@admin_only
async def admin_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    يعالج:
    1. سبب الرفض
    2. ملاحظة مشكلة التحويل
    3. إضافة لعبة (3 خطوات)
    4. إضافة باقة (3 خطوات)
    5. تعديل سعر باقة (2 خطوات)
    6. الإشعار الجماعي
    """
    text = update.message.text.strip() if update.message.text else ""
    flow = ctx.user_data.get("admin_flow")

    # ── رفض الطلب ─────────────────────────────
    if reject_id := ctx.user_data.pop("reject_order_id", None):
        reason = text if text != "-" else "لم يتم إثبات الدفع"
        order  = await get_order(reject_id)
        if order:
            await set_order_status(reject_id, S.REJECTED, note=reason, actor="admin")
            await update.message.reply_text(
                ADMIN_REJECTED_OK.format(order_id=reject_id, note=reason),
                parse_mode="Markdown",
            )
            try:
                await ctx.bot.send_message(
                    chat_id    = order["user_id"],
                    text       = ORDER_REJECTED.format(
                        order_id = order["id"],
                        note     = reason,
                        support  = SUPPORT_LINK,
                    ),
                    parse_mode = "Markdown",
                )
            except Exception as e:
                log.warning(f"[Notify reject] {e}")
        return

    # ── مشكلة تحويل ───────────────────────────
    if issue_id := ctx.user_data.pop("issue_order_id", None):
        order = await get_order(issue_id)
        if order:
            await set_order_status(issue_id, S.PAYMENT_SENT, note=text, actor="admin")
            await update.message.reply_text(f"✅ تم إرسال الملاحظة للعميل.")
            try:
                await ctx.bot.send_message(
                    chat_id    = order["user_id"],
                    text       = ORDER_ISSUE.format(
                        order_id = order["id"],
                        note     = text,
                        support  = SUPPORT_LINK,
                    ),
                    parse_mode = "Markdown",
                )
            except Exception as e:
                log.warning(f"[Notify issue] {e}")
        return

    # ── إضافة لعبة (3 خطوات) ─────────────────
    if flow == "add_game_key":
        if " " in text or not text.isascii():
            await update.message.reply_text("⚠️ المفتاح يجب أن يكون إنجليزي بدون مسافات.")
            return
        ctx.user_data["admin_game_key"] = text.lower()
        ctx.user_data["admin_flow"]     = "add_game_name"
        await update.message.reply_text(ADMIN_ASK_GAME_NAME, parse_mode="Markdown")
        return

    if flow == "add_game_name":
        ctx.user_data["admin_game_name"] = text
        ctx.user_data["admin_flow"]      = "add_game_emoji"
        await update.message.reply_text(ADMIN_ASK_GAME_EMOJI, parse_mode="Markdown")
        return

    if flow == "add_game_emoji":
        key   = ctx.user_data.pop("admin_game_key", "")
        name  = ctx.user_data.pop("admin_game_name", "")
        emoji = text
        ctx.user_data.pop("admin_flow", None)
        ok = await add_game(key, name, emoji)
        if ok:
            await update.message.reply_text(
                ADMIN_GAME_ADDED.format(name=name), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ فشل الإضافة — المفتاح موجود مسبقاً.")
        return

    # ── إضافة باقة (3 خطوات) ─────────────────
    if flow == "add_pkg_label":
        ctx.user_data["admin_pkg_label"] = text
        ctx.user_data["admin_flow"]      = "add_pkg_price"
        await update.message.reply_text(ADMIN_ASK_PKG_PRICE, parse_mode="Markdown")
        return

    if flow == "add_pkg_price":
        try:
            ctx.user_data["admin_pkg_price"] = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً.")
            return
        ctx.user_data["admin_flow"] = "add_pkg_cost"
        await update.message.reply_text(ADMIN_ASK_PKG_COST, parse_mode="Markdown")
        return

    if flow == "add_pkg_cost":
        try:
            cost = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً.")
            return
        game_key = ctx.user_data.pop("admin_game_key", "")
        label    = ctx.user_data.pop("admin_pkg_label", "")
        price    = ctx.user_data.pop("admin_pkg_price", 0)
        ctx.user_data.pop("admin_flow", None)
        await add_package(game_key, label, price, "دج", cost)
        await update.message.reply_text(
            ADMIN_PKG_ADDED.format(label=label, amount=price),
            parse_mode="Markdown",
        )
        return

    # ── تعديل سعر باقة (2 خطوات) ────────────
    if flow == "edit_pkg_price":
        try:
            ctx.user_data["admin_new_price"] = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً.")
            return
        ctx.user_data["admin_flow"] = "edit_pkg_cost"
        await update.message.reply_text(ADMIN_ASK_NEW_COST, parse_mode="Markdown")
        return

    if flow == "edit_pkg_cost":
        try:
            cost = float(text)
        except ValueError:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً.")
            return
        pkg_id = ctx.user_data.pop("admin_pkg_id", None)
        price  = ctx.user_data.pop("admin_new_price", 0)
        ctx.user_data.pop("admin_flow", None)
        if pkg_id:
            await update_package_price(pkg_id, price, cost)
            await update.message.reply_text(ADMIN_PKG_UPDATED, parse_mode="Markdown")
        return

    # ── الإشعار الجماعي ────────────────────────
    if flow == "broadcast":
        ctx.user_data.pop("admin_flow", None)
        user_ids = await get_all_user_ids()
        count    = 0
        for uid in user_ids:
            try:
                await ctx.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
                count += 1
            except Exception:
                pass
        await update.message.reply_text(
            ADMIN_BROADCAST_DONE.format(count=count), parse_mode="Markdown"
        )
        return
