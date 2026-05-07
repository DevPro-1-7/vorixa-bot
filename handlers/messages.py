"""
CharglyBot V3 — قوالب الرسائل الكاملة
"""
from datetime import datetime
from core.config import PAYMENT_NUMBER, PAYMENT_NAME, SUPPORT_LINK, PAYMENT_TIMEOUT_MINUTES


# ══════════════════════════════════════════════════
#  رسائل المستخدم — تدفق الطلب
# ══════════════════════════════════════════════════

WELCOME = """\
⚡ *مرحباً بك في CharglyBot*
_by diigiure_

🎮 منصة شحن ألعاب احترافية
🔒 نظام موافقة قبل الدفع — ضمان 100%
⚡ إشعارات فورية في كل خطوة

اختر من القائمة 👇\
"""

STEP_GAME = """\
🎮 *اختر اللعبة*

متاح الآن:\
"""

STEP_PLAYER_ID = """\
*الخطوة 1/3*

🔢 أدخل *Player ID* في لعبة {game_name}:

💡 _الملف الشخصي داخل اللعبة ← انسخ الـ ID_\
"""

STEP_PLAYER_NAME = """\
✅ Player ID: `{player_id}`

*الخطوة 2/3*

📛 أدخل *اسمك داخل اللعبة* (Nickname):\
"""

STEP_SCREENSHOT = """\
✅ الاسم: *{player_name}*

*الخطوة 3/3*

📸 أرسل *صورة بروفايلك* داخل اللعبة
_(تظهر فيها الـ ID + الاسم بوضوح)_\
"""

STEP_PACKAGE = """\
✅ تم استلام الصورة

💎 *اختر الباقة المطلوبة:*\
"""

ORDER_SUBMITTED = """\
✅ *تم تقديم طلبك بنجاح!*

🔢 رقم الطلب: *#{order_id}*
{game_emoji} اللعبة: *{game_name}*
🔢 Player ID: `{player_id}`
📛 الاسم: *{player_name}*
📦 الباقة: {package_label}
💰 السعر: *{amount:.0f} {currency}*
🕒 {time}

━━━━━━━━━━━━━━━━━━━━
🔍 *الطلب قيد المراجعة*

سيصلك إشعار فور موافقة الأدمن.
_لا تحتاج لإرسال أي مبلغ الآن._

📦 تابع طلبك: *طلباتي*\
"""

# ── بعد موافقة الأدمن ───────────────────────────

PAYMENT_DETAILS = """\
✅ *تمت الموافقة على طلبك!*

🔢 رقم الطلب: *#{order_id}*
{game_emoji} اللعبة: *{game_name}*
📦 الباقة: *{package_label}*
💰 المبلغ: *{amount:.0f} {currency}*

━━━━━━━━━━━━━━━━━━━━
💳 *تفاصيل التحويل:*
📱 الرقم: `{payment_number}`
👤 الاسم: *{payment_name}*
━━━━━━━━━━━━━━━━━━━━

⏰ لديك *{timeout} دقيقة* لإتمام الدفع
⚠️ _حوّل المبلغ المحدد بالضبط_

بعد التحويل اضغط الزر أدناه 👇\
"""

ASK_PROOF = """\
📸 *أرسل صورة إثبات التحويل*

_(لقطة شاشة تُظهر المبلغ + المستلم + الوقت)_\
"""

PROOF_RECEIVED = """\
🔒 *تم استلام إثبات الدفع*

🔢 رقم الطلب: *#{order_id}*
⚡ الطلب الآن محمي — لن يُلغى

⏳ جاري مراجعة التحويل...
سيصلك إشعار فور تأكيد الشحن.\
"""

ORDER_PROCESSING = """\
⚡ *طلبك قيد التنفيذ الآن!*

🔢 رقم الطلب: *#{order_id}*
{game_emoji} {game_name} — {package_label}

سيصلك إشعار عند اكتمال الشحن 🎮\
"""

ORDER_COMPLETED = """\
🎉 *تم الشحن بنجاح!*

🔢 رقم الطلب: *#{order_id}*
{game_emoji} {game_name}
💎 {package_label}
🔢 Player ID: `{player_id}`

شكراً لثقتك بنا! 🙏🔥\
"""

ORDER_REJECTED = """\
❌ *تم رفض طلبك*

🔢 رقم الطلب: *#{order_id}*
📝 السبب: _{note}_

للاستفسار: {support}\
"""

ORDER_EXPIRED = """\
⏰ *انتهت مهلة الدفع*

🔢 رقم الطلب: *#{order_id}*
_لم يتم استلام الدفع خلال {timeout} دقيقة._

يمكنك تقديم طلب جديد متى شئت 👇\
"""

ORDER_ISSUE = """\
⚠️ *مشكلة في التحويل*

🔢 رقم الطلب: *#{order_id}*
📝 ملاحظة الأدمن: _{note}_

يرجى التواصل مع الدعم: {support}\
"""

# ── تعديل الطلب ──────────────────────────────────

EDIT_MENU = """\
✏️ *تعديل الطلب #{order_id}*

{game_emoji} {game_name} — {package_label}
🔢 `{player_id}` | 📛 {player_name}

⚠️ _التعديل مسموح فقط قبل موافقة الأدمن_

اختر ما تريد تعديله:\
"""

EDIT_ASK_PID    = "🔢 أدخل *Player ID* الجديد:"
EDIT_ASK_NAME   = "📛 أدخل *الاسم* الجديد داخل اللعبة:"
EDIT_ASK_PHOTO  = "📸 أرسل *الصورة الجديدة* من بروفايلك:"
EDIT_DONE       = "✅ تم التعديل بنجاح!"
EDIT_LOCKED     = "🔒 لا يمكن تعديل الطلب بعد موافقة الأدمن."
EDIT_NO_ORDER   = "📦 لا يوجد طلب نشط قابل للتعديل."

ORDER_CANCELLED_USER = "🚫 تم إلغاء طلبك #{order_id} بنجاح."
ORDER_CANCEL_LOCKED  = "🔒 لا يمكن إلغاء الطلب في مرحلته الحالية."

# ── متنوع ──────────────────────────────────────

NO_ORDERS    = "📦 *طلباتي*\n\nلا توجد طلبات بعد.\nاضغط 🎮 شحن الآن!"
CANCELLED    = "❌ تم الإلغاء. يمكنك البدء من جديد."
RATE_LIMIT   = "⏳ انتظر لحظة قبل الإرسال مجدداً."
BANNED       = "⛔ تم حظرك من استخدام البوت."
BAD_ID       = "⚠️ الـ ID يجب أن يكون أرقاماً فقط (6–12 رقم). أعد الإدخال:"
BAD_NAME     = "⚠️ الاسم يجب أن يكون 2–24 حرف. أعد الإدخال:"
NOT_PHOTO    = "⚠️ يرجى إرسال *صورة*. أعد الإرسال:"
ACTIVE_ORDER = "⚠️ لديك طلب نشط بالفعل.\n\nتابعه من *📦 طلباتي* أو عدّله من *✏️ تعديل طلبي*."

SUPPORT_MSG = """\
📞 *الدعم الفني*

للتواصل: {support}
⏰ متاح: 8 ص – 12 م
⚡ متوسط الرد: أقل من 30 دقيقة\
"""


# ══════════════════════════════════════════════════
#  رسائل الأدمن
# ══════════════════════════════════════════════════

ADMIN_NEW_ORDER = """\
🔔 *طلب جديد للمراجعة — #{order_id}*

👤 {full_name} (`{user_id}`)
{game_emoji} اللعبة: *{game_name}*
🔢 Player ID: `{player_id}`
📛 الاسم: *{player_name}*
📦 الباقة: {package_label}
💰 السعر: *{amount:.0f} {currency}*
📈 الربح: *{profit:.0f} {currency}*
🕒 {time}

⬇️ راجع الصورة ثم اختر:\
"""

ADMIN_PROOF_RECEIVED = """\
🔒 *إثبات دفع — طلب #{order_id}* _(محمي)_

👤 {full_name} (`{user_id}`)
{game_emoji} {game_name} — {package_label}
🔢 Player ID: `{player_id}`
💰 *{amount:.0f} {currency}*
⏰ {time}

⬇️ راجع صورة التحويل:\
"""

ADMIN_STATS = """\
📊 *إحصائيات CharglyBot*

*━━ اليوم ━━*
📥 إجمالي الطلبات:   *{total}*
🔍 قيد المراجعة:     *{pending}*
💳 إثبات دفع معلق:   *{waiting}*
⚡ قيد التنفيذ:      *{processing}*
✅ مكتملة:           *{completed}*
❌ مرفوضة:           *{rejected}*
⏰ منتهية المهلة:     *{expired}*
💰 الإيرادات:        *{revenue:.0f} دج*
📈 صافي الربح:       *{profit:.0f} دج*
📊 معدل الإكمال:     *{rate}%*

*━━ هذا الأسبوع ━━*
💰 الإيرادات:        *{w_revenue:.0f} دج*
📈 صافي الربح:       *{w_profit:.0f} دج*

*━━ الأكثر طلباً ━━*
🎮 اللعبة:           *{top_game}*
📦 الباقة:           *{top_pkg}*

*━━ إجمالي ━━*
📦 كل الطلبات:       *{all_time}*
👥 المستخدمون:       *{users}*\
"""

ADMIN_APPROVED_OK  = "✅ تمت الموافقة على الطلب *#{order_id}* — تم إرسال تفاصيل الدفع."
ADMIN_COMPLETED_OK = "🎉 تم تأكيد الشحن للطلب *#{order_id}*"
ADMIN_PROCESSING_OK= "⚡ الطلب *#{order_id}* وُضع قيد التنفيذ — سيُشعر العميل."
ADMIN_REJECTED_OK  = "❌ تم رفض الطلب *#{order_id}*\nالسبب: {note}"
ADMIN_ALREADY_DONE = "ℹ️ هذا الطلب تمت معالجته مسبقاً."
ADMIN_PROTECTED    = "🔒 هذا الطلب محمي — لا يمكن رفضه بعد إرسال إثبات الدفع."
ADMIN_ASK_REASON   = "📝 أرسل سبب الرفض (أو `-` للتخطي):"
ADMIN_ASK_ISSUE    = "📝 أرسل ملاحظتك للعميل حول مشكلة التحويل:"

# إدارة الألعاب
ADMIN_ASK_GAME_KEY   = "🔑 أرسل *مفتاح اللعبة* (بالإنجليزية، بدون مسافات):\nمثال: `mobilelegends`"
ADMIN_ASK_GAME_NAME  = "📛 أرسل *اسم اللعبة* بالعربية:\nمثال: `موبايل ليجندز`"
ADMIN_ASK_GAME_EMOJI = "🎨 أرسل *إيموجي* اللعبة:\nمثال: `⚔️`"
ADMIN_GAME_ADDED     = "✅ تمت إضافة اللعبة *{name}* بنجاح!"
ADMIN_GAME_TOGGLED   = "🔄 تم تغيير حالة *{name}*"
ADMIN_GAME_DELETED   = "🗑️ تم حذف اللعبة *{name}* وجميع باقاتها."

# إدارة الباقات
ADMIN_ASK_PKG_LABEL    = "📝 أرسل *اسم الباقة*:\nمثال: `💎 500 جوهرة`"
ADMIN_ASK_PKG_PRICE    = "💰 أرسل *سعر البيع* (دج):"
ADMIN_ASK_PKG_COST     = "📈 أرسل *سعر التكلفة* (دج):"
ADMIN_PKG_ADDED        = "✅ تمت إضافة الباقة *{label}* بسعر *{amount:.0f} دج*"
ADMIN_PKG_TOGGLED      = "🔄 تم تغيير حالة الباقة."
ADMIN_PKG_DELETED      = "🗑️ تم حذف الباقة."
ADMIN_ASK_NEW_PRICE    = "💰 أرسل *السعر الجديد للبيع* (دج):"
ADMIN_ASK_NEW_COST     = "📈 أرسل *التكلفة الجديدة* (دج):"
ADMIN_PKG_UPDATED      = "✅ تم تحديث الباقة بنجاح."

# إشعار جماعي
ADMIN_ASK_BROADCAST    = "📢 أرسل نص *الإشعار الجماعي*:"
ADMIN_BROADCAST_DONE   = "✅ تم إرسال الإشعار لـ *{count}* مستخدم."


# ══════════════════════════════════════════════════
#  دوال مساعدة
# ══════════════════════════════════════════════════

STATUS_AR = {
    "awaiting_approval":    "🔍 قيد المراجعة",
    "waiting_payment":      "💳 انتظار الدفع",
    "payment_sent":         "🔒 إثبات بانتظار التأكيد",
    "processing":           "⚡ قيد التنفيذ",
    "completed":            "✅ تم الشحن",
    "rejected":             "❌ مرفوض",
    "expired":              "⏰ انتهت المهلة",
    "cancelled":            "🚫 ملغي",
}


def fmt_order_row(o: dict) -> str:
    status = STATUS_AR.get(o["status"], o["status"])
    note   = f"\n📝 _{o['note']}_" if o.get("note") else ""
    return (
        f"🔢 *#{o['id']}* — {status}\n"
        f"🎮 {o.get('game_name','—')} | {o['package_label']}\n"
        f"👤 {o.get('player_name','—')} | ID: `{o['player_id']}`\n"
        f"💰 {o['amount']:.0f} {o['currency']}"
        f"{note}\n"
        f"─────────────────\n"
    )


def fmt_payment_msg(o: dict) -> str:
    return PAYMENT_DETAILS.format(
        order_id       = o["id"],
        game_emoji     = "",
        game_name      = o["game_name"],
        package_label  = o["package_label"],
        amount         = o["amount"],
        currency       = o["currency"],
        payment_number = PAYMENT_NUMBER,
        payment_name   = PAYMENT_NAME,
        timeout        = PAYMENT_TIMEOUT_MINUTES,
    )


def now_str() -> str:
    return datetime.now().strftime("%H:%M — %d/%m/%Y")
