"""
handlers/student.py
-------------------
Handles the full student report-submission flow using FSM states.
Detects admin on /start and redirects them to the admin panel.
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, ALL_DEPARTMENTS, COLLEGES, DEPARTMENTS, SUPER_ADMIN_ID
from database import check_existing_submission, save_report
from utils import fmt_time
from keyboards import (
    admin_main_inline_keyboard,
    admin_reply_keyboard,
    college_keyboard,
    department_keyboard,
    remove_keyboard,
)
from states import ReportForm

logger = logging.getLogger(__name__)
router = Router(name="student")

# Support contact message — reused in /help and rejection messages
SUPPORT_TEXT = (
    "📞 *للتواصل مع الدعم:*\n"
    "• @a_iqi202\n"
    "• @n_zankana\n"
    "_يمكنك مراسلتنا مباشرة عبر الرسائل الخاصة._"
)


# ──────────────────────────────────────────────
# /start  →  admin gets admin panel, student gets name prompt
# ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Entry point.
    - If the user is the admin: show the admin panel with persistent keyboard.
    - Otherwise: start the student submission flow.
    """
    await state.clear()

    # ── Admin branch (admin AND superadmin both get the admin panel) ──
    if message.from_user.id in (ADMIN_ID, SUPER_ADMIN_ID):  # type: ignore[union-attr]
        await message.answer(
            "مرحباً يا دكتور 👋\nأهلاً بك في لوحة تحكم إدارة التقارير.\n"
            "يمكنك استخدام الأزرار أدناه في أي وقت:",
            reply_markup=admin_reply_keyboard(),
        )
        await message.answer(
            "اختر ما تريد من الخيارات:",
            reply_markup=admin_main_inline_keyboard(),
        )
        return

    # ── Student branch ──
    await state.set_state(ReportForm.awaiting_name)
    await message.answer(
        "مرحباً بك في بوت تسليم تقارير مادة اللغة العربية. "
        "يرجى إرسال اسمك الثلاثي الكامل للبدء:",
        reply_markup=remove_keyboard(),   # make sure no stale keyboard is shown
    )
# ──────────────────────────────────────────────
# /help  →  show support contacts
# ──────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show support contacts to anyone who needs help."""
    await message.answer(
        "🚨 *هل تواجه مشكلة؟*\n\n"
        "لا تقلق، نحن هنا لمساعدتك! تواصل معنا مباشرة:\n\n"
        + SUPPORT_TEXT,
        parse_mode="Markdown",
    )



# ──────────────────────────────────────────────
# AWAITING_NAME  →  save name, show college picker
# ──────────────────────────────────────────────

@router.message(ReportForm.awaiting_name)
async def handle_name(message: Message, state: FSMContext) -> None:
    """Receive the student's full name and move to college selection."""
    full_name = (message.text or "").strip()

    if not full_name or len(full_name) < 3:
        await message.answer("يرجى إدخال اسمك الثلاثي الكامل (ثلاث كلمات على الأقل).")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(ReportForm.awaiting_college)

    await message.answer(
        "شكراً لك. الآن اختر كليتك من القائمة أدناه:",
        reply_markup=college_keyboard(),
    )


# ──────────────────────────────────────────────
# AWAITING_COLLEGE  →  save college, show department picker
# ──────────────────────────────────────────────

@router.callback_query(ReportForm.awaiting_college, F.data.in_({"college_excellence", "college_ai"}))
async def handle_college(callback: CallbackQuery, state: FSMContext) -> None:
    """Receive college selection and display the relevant departments."""
    college_callback = callback.data
    college_name     = COLLEGES[college_callback]

    await state.update_data(college=college_name, college_callback=college_callback)
    await state.set_state(ReportForm.awaiting_department)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "ممتاز. الآن اختر قسمك الأكاديمي:",
        reply_markup=department_keyboard(college_callback),
    )
    await callback.answer()


# ──────────────────────────────────────────────
# AWAITING_DEPARTMENT  →  save dept, ask for Word file
# ──────────────────────────────────────────────

@router.callback_query(ReportForm.awaiting_department, F.data.in_(ALL_DEPARTMENTS.keys()))
async def handle_department(callback: CallbackQuery, state: FSMContext) -> None:
    """Receive department selection and ask for the Word report."""
    dept_callback = callback.data
    dept_name     = ALL_DEPARTMENTS[dept_callback]

    await state.update_data(department=dept_name)
    await state.set_state(ReportForm.awaiting_report)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "خطوة أخيرة: يرجى إرسال تقرير اللغة العربية بصيغة (Word) حصراً. (.doc أو .docx)"
    )
    await callback.answer()


# ──────────────────────────────────────────────
# AWAITING_REPORT  →  validate Word → save → notify
# ──────────────────────────────────────────────

@router.message(ReportForm.awaiting_report)
async def handle_report(message: Message, state: FSMContext) -> None:
    """
    Receive the student's Word file (.doc / .docx).

    - Reject anything that is not a Word document.
    - On valid Word file: save to DB, confirm to student, forward details to admin.
    """
    # ── Accepted Word MIME types ──
    WORD_MIME_TYPES = {
        "application/msword",                                                          # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",     # .docx
    }

    # ── Validate: must be a Word document ──
    doc = message.document
    if not doc or doc.mime_type not in WORD_MIME_TYPES:
        await message.answer(
            "عذراً، يجب إرسال الملف بصيغة Word فقط! (.doc أو .docx) يرجى إعادة المحاولة."
        )
        return

    telegram_id = message.from_user.id  # type: ignore[union-attr]

    # ── One-submission rule: reject if already submitted ──
    already_submitted = await check_existing_submission(telegram_id)
    if already_submitted:
        await state.clear()
        await message.answer(
            "⚠️ لقد قمت بتسليم تقريرك مسبقاً ولا يمكنك التسليم مرة أخرى.\n\n"
            "إذا كنت بحاجة لإعادة التسليم، تواصل مع الدعم:\n\n"
            + SUPPORT_TEXT,
            parse_mode="Markdown",
        )
        return

    # ── Retrieve stored FSM data ──
    data        = await state.get_data()
    full_name   = data["full_name"]
    college     = data["college"]
    department  = data["department"]
    file_id     = doc.file_id

    # ── Persist to database ──
    submission_time: datetime = await save_report(
        telegram_id=telegram_id,
        full_name=full_name,
        college=college,
        department=department,
        file_id=file_id,
    )

    # ── Clear FSM state ──
    await state.clear()

    # ── Confirm to student ──
    await message.answer("تم استلام تقريرك بنجاح! شكراً لك وتم تسجيل معلوماتك. ✅")

    # ── Forward to admin with metadata ──
    formatted_time = fmt_time(submission_time)
    admin_caption = (
        "📥 *تقرير جديد تم استلامه:*\n\n"
        f"👤 *الاسم:* {full_name}\n"
        f"🏫 *الكلية:* {college}\n"
        f"🎓 *القسم:* {department}\n"
        f"⏰ *الوقت:* {formatted_time}"
    )

    try:
        await message.bot.send_document(  # type: ignore[union-attr]
            chat_id=ADMIN_ID,
            document=file_id,
            caption=admin_caption,
            parse_mode="Markdown",
        )
        logger.info(
            "Report forwarded to admin. Student: %s | Dept: %s", full_name, department
        )
    except Exception as exc:
        logger.error("Failed to forward report to admin (ID=%s): %s", ADMIN_ID, exc)


# ──────────────────────────────────────────────
# Fallback: stray messages during inline-keyboard states
# ──────────────────────────────────────────────

@router.message(ReportForm.awaiting_college)
@router.message(ReportForm.awaiting_department)
async def handle_unexpected_text(message: Message) -> None:
    """Remind the student to use the inline keyboard buttons."""
    await message.answer("يرجى الاختيار من خلال الأزرار أعلاه.")
