"""
CharglyBot V3 — تخطيطات الأزرار الكاملة
"""
from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup  as IKM
from telegram import ReplyKeyboardMarkup   as RKM


# ══════════════════════════════════════════════════
#  أزرار المستخدم — القائمة الرئيسية
# ══════════════════════════════════════════════════

def kb_main() -> RKM:
    return RKM(
        [["🎮 شحن الآن"],
         ["📦 طلباتي", "✏️ تعديل طلبي"],
         ["📞 الدعم"]],
        resize_keyboard=True,
    )


# ══════════════════════════════════════════════════
#  تدفق تقديم الطلب
# ══════════════════════════════════════════════════

def kb_games(games: list[dict]) -> IKM:
    rows = [[Btn(f"{g['emoji']} {g['name']}", callback_data=f"game:{g['key']}")]
            for g in games]
    rows.append([Btn("❌ إلغاء", callback_data="cancel")])
    return IKM(rows)


def kb_packages(pkgs: list[dict]) -> IKM:
    rows = []
    for p in pkgs:
        rows.append([Btn(
            f"{p['label']}  —  {p['amount']:.0f} {p['currency']}",
            callback_data=f"pkg:{p['id']}"
        )])
    rows.append([Btn("🔙 رجوع", callback_data="back_game"),
                 Btn("❌ إلغاء", callback_data="cancel")])
    return IKM(rows)


def kb_cancel() -> IKM:
    return IKM([[Btn("❌ إلغاء", callback_data="cancel")]])


# ══════════════════════════════════════════════════
#  صفحة الطلب (عرض + تعديل)
# ══════════════════════════════════════════════════

def kb_order_view(order_id: int, can_edit: bool = True, can_cancel: bool = True) -> IKM:
    rows = []
    if can_edit:
        rows.append([Btn("✏️ تعديل الطلب", callback_data=f"edit:menu:{order_id}")])
    if can_cancel:
        rows.append([Btn("🗑️ إلغاء الطلب", callback_data=f"order:cancel:{order_id}")])
    return IKM(rows) if rows else None


def kb_edit_menu(order_id: int) -> IKM:
    return IKM([
        [Btn("🎮 تغيير اللعبة",   callback_data=f"edit:game:{order_id}"),
         Btn("📦 تغيير الباقة",   callback_data=f"edit:package:{order_id}")],
        [Btn("🔢 تعديل Player ID", callback_data=f"edit:pid:{order_id}"),
         Btn("📛 تعديل الاسم",     callback_data=f"edit:name:{order_id}")],
        [Btn("📸 إعادة رفع الصورة", callback_data=f"edit:photo:{order_id}")],
        [Btn("🔙 رجوع",            callback_data=f"edit:back:{order_id}")],
    ])


# ══════════════════════════════════════════════════
#  مرحلة الدفع (بعد موافقة الأدمن)
# ══════════════════════════════════════════════════

def kb_pay_action() -> IKM:
    return IKM([[Btn("✅ لقد قمت بالدفع — أرسل الإثبات", callback_data="pay:proof")]])


# ══════════════════════════════════════════════════
#  أزرار الأدمن — مراجعة الطلب الجديد
# ══════════════════════════════════════════════════

def kb_admin_review(order_id: int) -> IKM:
    return IKM([[
        Btn("✅ قبول الطلب",  callback_data=f"adm:approve:{order_id}"),
        Btn("❌ رفض",          callback_data=f"adm:reject:{order_id}"),
    ]])


def kb_admin_proof(order_id: int) -> IKM:
    """أزرار مراجعة إثبات الدفع — Protected Order لا يُرفض"""
    return IKM([[
        Btn("✅ تم الشحن",        callback_data=f"adm:complete:{order_id}"),
        Btn("⏳ قيد التنفيذ",     callback_data=f"adm:processing:{order_id}"),
        Btn("⚠️ مشكلة بالتحويل", callback_data=f"adm:issue:{order_id}"),
    ]])


def kb_admin_processing(order_id: int) -> IKM:
    return IKM([[
        Btn("✅ تم الشحن الآن", callback_data=f"adm:complete:{order_id}"),
    ]])


def kb_admin_panel() -> IKM:
    return IKM([
        [Btn("📋 مراجعة",      callback_data="adm:list:awaiting_approval"),
         Btn("💳 إثباتات دفع", callback_data="adm:list:payment_sent")],
        [Btn("⚡ قيد التنفيذ", callback_data="adm:list:processing"),
         Btn("✅ مكتملة",       callback_data="adm:list:completed")],
        [Btn("📊 إحصائيات",    callback_data="adm:stats"),
         Btn("📋 كل الطلبات",  callback_data="adm:list:all")],
        [Btn("🎮 إدارة الألعاب",  callback_data="adm:games"),
         Btn("📢 إشعار جماعي",   callback_data="adm:broadcast")],
    ])


def kb_admin_games(games: list[dict]) -> IKM:
    rows = []
    for g in games:
        status = "✅" if g["is_active"] else "⏸️"
        rows.append([
            Btn(f"{status} {g['emoji']} {g['name']}", callback_data=f"adm:g:pkgs:{g['key']}"),
            Btn("🔄",  callback_data=f"adm:g:toggle:{g['key']}"),
            Btn("🗑️",  callback_data=f"adm:g:delete:{g['key']}"),
        ])
    rows.append([Btn("➕ إضافة لعبة جديدة", callback_data="adm:g:add")])
    rows.append([Btn("🔙 لوحة التحكم",      callback_data="adm:panel")])
    return IKM(rows)


def kb_admin_packages(pkgs: list[dict], game_key: str) -> IKM:
    rows = []
    for p in pkgs:
        status = "✅" if p["is_active"] else "⏸️"
        rows.append([
            Btn(f"{status} {p['label']} — {p['amount']:.0f} دج",
                callback_data=f"adm:p:edit:{p['id']}"),
            Btn("🔄", callback_data=f"adm:p:toggle:{p['id']}:{game_key}"),
            Btn("🗑️", callback_data=f"adm:p:delete:{p['id']}:{game_key}"),
        ])
    rows.append([Btn("➕ إضافة باقة",      callback_data=f"adm:p:add:{game_key}")])
    rows.append([Btn("🔙 إدارة الألعاب",   callback_data="adm:games")])
    return IKM(rows)


def kb_admin_back() -> IKM:
    return IKM([[Btn("🔙 لوحة التحكم", callback_data="adm:panel")]])
