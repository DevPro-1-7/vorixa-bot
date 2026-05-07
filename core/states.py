"""
CharglyBot V3 — State Machine

┌─────────────────────────────────────────────────┐
│               تدفق الطلب الكامل                  │
│                                                   │
│  DRAFT → AWAITING_APPROVAL                        │
│            ↓ approve                             │
│          WAITING_PAYMENT                          │
│            ↓ user pays + sends proof             │
│          PAYMENT_SENT  (Protected Order)          │
│            ↓ admin confirms                      │
│          PROCESSING                               │
│            ↓ done                                │
│          COMPLETED ✅                             │
│                                                   │
│  REJECTED ❌  (من أي مرحلة قبل PAYMENT_SENT)    │
│  EXPIRED  ⏰  (انتهت مهلة الدفع)                │
│  CANCELLED 🚫 (ألغاه المستخدم قبل الموافقة)    │
└─────────────────────────────────────────────────┘
"""


class S:
    """حالات قاعدة البيانات"""
    DRAFT               = "draft"                # مسودة (لم يكتمل بعد)
    AWAITING_APPROVAL   = "awaiting_approval"    # ينتظر مراجعة الأدمن
    WAITING_PAYMENT     = "waiting_payment"      # وافق الأدمن — ينتظر دفع العميل
    PAYMENT_SENT        = "payment_sent"         # 🔒 Protected — إثبات الدفع وصل
    PROCESSING          = "processing"           # قيد التنفيذ
    COMPLETED           = "completed"            # ✅ تم الشحن
    REJECTED            = "rejected"             # ❌ مرفوض
    EXPIRED             = "expired"              # ⏰ انتهت المهلة
    CANCELLED           = "cancelled"            # 🚫 ألغاه المستخدم

    # الحالات التي يمكن تعديل الطلب فيها
    EDITABLE = {DRAFT, AWAITING_APPROVAL}

    # الحالات النشطة (تمنع طلباً جديداً)
    ACTIVE = {DRAFT, AWAITING_APPROVAL, WAITING_PAYMENT, PAYMENT_SENT, PROCESSING}

    # الحالات النهائية
    TERMINAL = {COMPLETED, REJECTED, EXPIRED, CANCELLED}

    # Protected — الأدمن لا يستطيع الرفض
    PROTECTED = {PAYMENT_SENT, PROCESSING}


# ── خطوات ConversationHandler ───────────────────

# تقديم الطلب الجديد
STEP_GAME         = 10
STEP_PLAYER_ID    = 11
STEP_PLAYER_NAME  = 12
STEP_SCREENSHOT   = 13
STEP_PACKAGE      = 14

# تعديل الطلب (قبل الموافقة)
STEP_EDIT_MENU    = 20
STEP_EDIT_FIELD   = 21

# مرحلة الدفع
STEP_PAY_PROOF    = 30

# لوحة تحكم الأدمن
ADMIN_MAIN        = 40
ADMIN_ADD_GAME    = 41
ADMIN_ADD_PKG     = 42
ADMIN_EDIT_PRICE  = 43
ADMIN_BROADCAST   = 44
ADMIN_SET_COST    = 45
