"""
handlers/superadmin.py
----------------------
Superadmin-only commands and callbacks.

The superadmin has full control over the database AND inherits all admin rights:
  - /superadmin          → superadmin panel
  - sa_list_students     → all students as inline buttons
  - sa_view_{id}         → full details of one student + delete option
  - sa_delete_one        → student list in delete mode
  - sa_del_ask_{id}      → deletion confirmation screen
  - sa_del_exec_{id}     → execute deletion + notify student
  - sa_delete_all_ask    → confirm wiping everything
  - sa_delete_all_exec   → wipe all submissions
  - sa_cancel            → cancel, return to panel
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import SUPER_ADMIN_ID
from utils import fmt_time_str
from database import (
    delete_all_submissions,
    delete_submission_by_id,
    get_all_students_brief,
    get_submission_by_id,
)
from keyboards import (
    delete_all_confirm_keyboard,
    delete_confirm_keyboard,
    students_delete_keyboard,
    students_list_keyboard,
    superadmin_main_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="superadmin")


# ──────────────────────────────────────────────
# Guard helper
# ──────────────────────────────────────────────

def _is_superadmin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID


# ──────────────────────────────────────────────
# /superadmin command
# ──────────────────────────────────────────────

@router.message(Command("superadmin"))
async def cmd_superadmin(message: Message) -> None:
    """Show the superadmin panel or silently ignore non-superadmins."""
    if not _is_superadmin(message.from_user.id):  # type: ignore[union-attr]
        # Silent ignore — do not reveal that this command exists
        return

    students = await get_all_students_brief()
    total = len(students)

    await message.answer(
        f"🛡 *لوحة تحكم المشرف العام*\n\n"
        f"📦 إجمالي التقارير في قاعدة البيانات: *{total}*\n\n"
        "⚠️ هذه اللوحة تتيح لك حذف تقارير الطلاب للسماح لهم بإعادة التسليم.",
        reply_markup=superadmin_main_keyboard(),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# CALLBACK: sa_list_students — text list of all students
# ──────────────────────────────────────────────

@router.callback_query(F.data == "sa_list_students")
async def cb_sa_list_students(callback: CallbackQuery) -> None:
    """Show all submitted students as tappable inline buttons."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    students = await get_all_students_brief()

    if not students:
        await callback.message.answer("📭 لا يوجد أي تقارير مسجّلة حتى الآن.")  # type: ignore[union-attr]
        await callback.answer()
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"📋 *قائمة الطلاب المسجّلين* — الإجمالي: *{len(students)}* طالب\n"
        "_اضغط على اسم أي طالب لعرض تفاصيله كاملة:_",
        reply_markup=students_list_keyboard(students),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_view_{id} — show one student’s full details
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("sa_view_"))
async def cb_sa_view_student(callback: CallbackQuery) -> None:
    """
    Show the full details of one student's submission.
    Includes an inline button to delete their record directly from here.
    """
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    try:
        submission_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("معرّف غير صالح.", show_alert=True)
        return

    submission = await get_submission_by_id(submission_id)
    if not submission:
        await callback.message.answer(  # type: ignore[union-attr]
            "⚠️ لم يتم العثور على هذا التقرير. ربما تم حذفه مسبقاً."
        )
        await callback.answer()
        return

    # Build detail message
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🗑 حذف تقرير هذا الطالب",
            callback_data=f"sa_del_ask_{submission_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="sa_list_students")
    )

    await callback.message.answer(  # type: ignore[union-attr]
        f"👤 *تفاصيل الطالب*\n\n"
        f"📛 *رقم التسجيل:* `#{submission['id']}`\n"
        f"👤 *الاسم:* {submission['full_name']}\n"
        f"🏫 *الكلية:* {submission['college']}\n"
        f"🎓 *القسم:* {submission['department']}\n"
        f"🔑 *معرّف تيليغرام:* `{submission['telegram_id']}`\n"
        f"⏰ *وقت التسليم:* {fmt_time_str(submission['submission_time'])}\n",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()



# ──────────────────────────────────────────────
# CALLBACK: sa_delete_one — show deletable student list
# ──────────────────────────────────────────────

@router.callback_query(F.data == "sa_delete_one")
async def cb_sa_delete_one(callback: CallbackQuery) -> None:
    """Show all students as inline buttons — tapping one starts the deletion flow."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    students = await get_all_students_brief()

    if not students:
        await callback.message.answer("📭 لا يوجد أي تقارير لحذفها.")  # type: ignore[union-attr]
        await callback.answer()
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"🗑 *اختر الطالب الذي تريد حذف تقريره:*\n"
        f"_(سيتم إخطاره بإمكانية إعادة التسليم)_\n\n"
        f"العدد الكلي: *{len(students)}* طالب",
        reply_markup=students_delete_keyboard(students),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_del_ask_{id} — confirmation step
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("sa_del_ask_"))
async def cb_sa_del_ask(callback: CallbackQuery) -> None:
    """Ask the superadmin to confirm deletion of one specific student's report."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    try:
        submission_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("معرّف غير صالح.", show_alert=True)
        return

    submission = await get_submission_by_id(submission_id)
    if not submission:
        await callback.message.answer(  # type: ignore[union-attr]
            "⚠️ لم يتم العثور على هذا التقرير. ربما تم حذفه مسبقاً."
        )
        await callback.answer()
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"⚠️ *تأكيد الحذف*\n\n"
        f"👤 *الاسم:* {submission['full_name']}\n"
        f"🎓 *القسم:* {submission['department']}\n"
        f"🏫 *الكلية:* {submission['college']}\n"
        f"⏰ *وقت التسليم:* {fmt_time_str(submission['submission_time'])}\n\n"
        f"هل أنت متأكد من حذف هذا التقرير؟\n"
        f"_سيتم إخطار الطالب بأنه يستطيع إعادة التسليم._",
        reply_markup=delete_confirm_keyboard(submission_id),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_del_exec_{id} — execute single deletion
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("sa_del_exec_"))
async def cb_sa_del_exec(callback: CallbackQuery) -> None:
    """
    Execute deletion of one submission:
    1. Delete from DB.
    2. Confirm to superadmin.
    3. Notify the student they can resubmit by sending /start.
    """
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    try:
        submission_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("معرّف غير صالح.", show_alert=True)
        return

    # Fetch before deleting so we still have the student's telegram_id and name
    submission = await get_submission_by_id(submission_id)
    if not submission:
        await callback.message.answer(  # type: ignore[union-attr]
            "⚠️ التقرير غير موجود — ربما تم حذفه مسبقاً."
        )
        await callback.answer()
        return

    deleted = await delete_submission_by_id(submission_id)

    if not deleted:
        await callback.message.answer(  # type: ignore[union-attr]
            "❌ فشل الحذف. يرجى المحاولة مرة أخرى."
        )
        await callback.answer()
        return

    # ── Confirm to superadmin ──
    await callback.message.answer(  # type: ignore[union-attr]
        f"✅ *تم حذف تقرير الطالب بنجاح:*\n\n"
        f"👤 {submission['full_name']} — {submission['department']}",
        parse_mode="Markdown",
    )

    # ── Notify the student ──
    try:
        await callback.message.bot.send_message(  # type: ignore[union-attr]
            chat_id=submission["telegram_id"],
            text=(
                "📢 *إشعار مهم:*\n\n"
                "لقد قام الأستاذ بإعادة ضبط تقريرك، ويمكنك الآن إعادة تسليم "
                "تقرير مادة اللغة العربية.\n\n"
                "اضغط /start للبدء من جديد."
            ),
            parse_mode="Markdown",
        )
        logger.info(
            "Student %s (id=%s) notified about resubmission.",
            submission["full_name"], submission["telegram_id"],
        )
    except Exception as exc:
        logger.warning(
            "Could not notify student telegram_id=%s: %s",
            submission["telegram_id"], exc,
        )
        await callback.message.answer(  # type: ignore[union-attr]
            "⚠️ تم الحذف لكن فشل إرسال الإشعار للطالب (ربما لم يبدأ محادثة مع البوت)."
        )

    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_delete_all_ask — ask confirmation to wipe all
# ──────────────────────────────────────────────

@router.callback_query(F.data == "sa_delete_all_ask")
async def cb_sa_delete_all_ask(callback: CallbackQuery) -> None:
    """Ask for confirmation before deleting ALL submissions."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    students = await get_all_students_brief()
    count = len(students)

    await callback.message.answer(  # type: ignore[union-attr]
        f"🛡 *تحذير: حذف جميع التقارير*\n\n"
        f"سيتم حذف *{count}* تقرير من قاعدة البيانات بشكل نهائي.\n"
        f"⚠️ *هذا الإجراء لا يمكن التراجع عنه.*\n\n"
        f"هل أنت متأكد تماماً؟",
        reply_markup=delete_all_confirm_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_delete_all_exec — execute wipe
# ──────────────────────────────────────────────

@router.callback_query(F.data == "sa_delete_all_exec")
async def cb_sa_delete_all_exec(callback: CallbackQuery) -> None:
    """Wipe the entire students_reports table."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    count = await delete_all_submissions()

    await callback.message.answer(  # type: ignore[union-attr]
        f"✅ *تم حذف جميع التقارير بنجاح.*\n"
        f"🗑 عدد السجلات المحذوفة: *{count}*",
        parse_mode="Markdown",
    )
    logger.warning("Superadmin wiped all %s submissions.", count)
    await callback.answer()


# ──────────────────────────────────────────────
# CALLBACK: sa_cancel — cancel any pending action
# ──────────────────────────────────────────────

@router.callback_query(F.data == "sa_cancel")
async def cb_sa_cancel(callback: CallbackQuery) -> None:
    """Cancel and return to superadmin panel."""
    if not _is_superadmin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    students = await get_all_students_brief()
    await callback.message.answer(  # type: ignore[union-attr]
        f"↩️ تم الإلغاء.\n\n"
        f"🛡 *لوحة تحكم المشرف العام*\n"
        f"📦 إجمالي التقارير: *{len(students)}*",
        reply_markup=superadmin_main_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()
