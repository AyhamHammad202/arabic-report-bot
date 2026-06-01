"""
handlers/admin.py
-----------------
Admin-only commands and callbacks.

Navigation:
  /start or /admin         → main panel (inline) + persistent reply keyboard
  Reply "📊 الإحصائيات"    → stats
  Reply "📁 ملفات الأقسام" → dept picker
  Reply "📋 جميع ملفات"    → all files
  Reply "🏠 القائمة"       → back to main
  Inline: admin_stats, admin_view_depts, admin_view_all, view_dept_*, admin_back
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, ALL_DEPARTMENTS, SUPER_ADMIN_ID
from database import get_all_reports, get_all_departments, get_reports_by_department, get_stats
from utils import fmt_time_str
from keyboards import (
    ALL_DEPT_NAMES,
    admin_departments_reply_keyboard,
    admin_main_inline_keyboard,
    admin_reply_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="admin")


# ──────────────────────────────────────────────
# Guard helper
# ──────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    """Return True for the admin OR the superadmin (who inherits all admin rights)."""
    return user_id in (ADMIN_ID, SUPER_ADMIN_ID)


# ──────────────────────────────────────────────
# Shared helper: send the main admin panel
# ──────────────────────────────────────────────

async def _send_admin_panel(message: Message) -> None:
    """Send the admin welcome panel with persistent + inline keyboards."""
    stats  = await get_stats()
    total  = stats["total"]
    await message.answer(
        f"*لوحة تحكم التقارير*\n\n"
        f"إجمالي التقارير المستلمة حتى الآن: *{total}*\n\n"
        "اختر ما تريد من الخيارات:",
        reply_markup=admin_main_inline_keyboard(),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# /whoami  — debug: show caller's Telegram ID
# ──────────────────────────────────────────────

@router.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    """Debug — returns the caller's Telegram user ID."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    logger.info("/whoami called by user_id=%s", user_id)
    await message.answer(
        f"🔍 *معرّفك على تيليغرام هو:*\n`{user_id}`\n\n"
        f"تأكد أن هذا الرقم مطابق لقيمة `ADMIN_ID` في ملف `.env`",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# /admin command
# ──────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Show admin panel or reject non-admin users."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    logger.info(
        "/admin called | from_user.id=%s | ADMIN_ID=%s | match=%s",
        user_id, ADMIN_ID, user_id == ADMIN_ID,
    )

    if not _is_admin(user_id):
        await message.answer("عذراً، هذا الأمر خاص بأستاذ المادة فقط.")
        return

    # Restore persistent keyboard in case it was lost, then show panel
    await message.answer(
        "مرحباً يا دكتور 👋",
        reply_markup=admin_reply_keyboard(),
    )
    await _send_admin_panel(message)


# ──────────────────────────────────────────────
# Persistent reply keyboard button handlers
# These fire when the admin taps a bottom-keyboard button
# ──────────────────────────────────────────────

@router.message(F.text == "القائمة الرئيسية")
async def reply_main_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await _send_admin_panel(message)


@router.message(F.text == "الإحصائيات")
async def reply_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await _deliver_stats(message)


@router.message(F.text == "ملفات الأقسام")
async def reply_view_depts(message: Message) -> None:
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await message.answer(
        "اختر القسم الذي تريد استعراض تقاريره:",
        reply_markup=admin_departments_reply_keyboard(),
    )


# ── College-header buttons (visual labels, not actionable) ──
@router.message(F.text.in_({"كلية التميز", "كلية الذكاء الاصطناعي"}))
async def reply_college_header(message: Message) -> None:
    """The college-name rows are visual separators; remind admin to tap a department."""
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await message.answer("اختر أحد الأقسام الموجودة أسفله.")


# ── Department name taps (reply keyboard) ──
@router.message(F.text.in_(ALL_DEPT_NAMES))
async def reply_dept_selected(message: Message) -> None:
    """Admin tapped a department button — send all PDFs for that department."""
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    dept_name = message.text
    await _deliver_dept_reports(message, dept_name)


# ── Back button (dept keyboard → main admin keyboard) ──
@router.message(F.text == "رجوع للقائمة الرئيسية")
async def reply_back_to_main(message: Message) -> None:
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await message.answer(
        "القائمة الرئيسية:",
        reply_markup=admin_reply_keyboard(),
    )
    await _send_admin_panel(message)


@router.message(F.text == "جميع ملفات الطلاب")
async def reply_view_all(message: Message) -> None:
    if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
        return
    await _deliver_all_reports(message)


# ──────────────────────────────────────────────
# Shared delivery functions (used by both reply & inline paths)
# ──────────────────────────────────────────────

async def _deliver_stats(target: Message) -> None:
    """Build and send the statistics message."""
    stats    = await get_stats()
    by_dept  = stats["by_department"]
    total    = stats["total"]

    def count(dept_name: str) -> int:
        return by_dept.get(dept_name, 0)

    text = (
        "*إحصائيات تسليم التقارير الحالية:*\n\n"

        "*كلية التميز:*\n"
        f"  - نظم المعلومات التطبيقية: *{count('نظم المعلومات التطبيقية')}*\n"
        f"  - علم البيانات: *{count('علم البيانات')}*\n"
        f"  - الفلسفة وعلم الاجتماع: *{count('الفلسفة وعلم الاجتماع')}*\n"
        f"  - المحاسبة والمصارف: *{count('المحاسبة والمصارف')}*\n"
        f"  - إدارة الأعمال والتجارة الإلكترونية: *{count('إدارة الأعمال والتجارة الإلكترونية')}*\n\n"

        "*كلية الذكاء الاصطناعي:*\n"
        f"  - التطبيقات الهندسية: *{count('التطبيقات الهندسية')}*\n"
        f"  - البيانات الضخمة: *{count('البيانات الضخمة')}*\n"
        f"  - التطبيقات الطبية الحيوية: *{count('التطبيقات الطبية الحيوية')}*\n\n"

        f"*إجمالي التقارير المستلمة:* *{total}*"
    )
    await target.answer(text, parse_mode="Markdown")


async def _deliver_all_reports(target: Message) -> None:
    """Fetch every report and send each PDF to the admin."""
    reports = await get_all_reports()

    if not reports:
        await target.answer("لا توجد تقارير مسلّمة بعد.")
        return

    await target.answer(
        f"*جميع ملفات الطلاب المستلمة*\nالإجمالي: *{len(reports)}* تقرير",
        parse_mode="Markdown",
    )

    for idx, report in enumerate(reports, start=1):
        caption = (
            f"تقرير رقم {idx}\n"
            f"الاسم: {report['full_name']}\n"
            f"الكلية: {report['college']}\n"
            f"القسم: {report['department']}\n"
            f"وقت التسليم: {fmt_time_str(report['submission_time'])}"
        )
        try:
            await target.bot.send_document(  # type: ignore[union-attr]
                chat_id=target.chat.id,
                document=report["file_id"],
                caption=caption,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error(
                "Failed to send report #%s (%s) to admin: %s",
                idx, report["full_name"], exc,
            )
            # Fallback to text message if document fails to send (e.g. invalid file_id)
            fallback_text = (
                f"{caption}\n"
                f"(ملاحظة: تعذر إرسال الملف المرفق)"
            )
            await target.bot.send_message(  # type: ignore[union-attr]
                chat_id=target.chat.id,
                text=fallback_text,
                parse_mode="Markdown",
            )


async def _deliver_dept_reports(target: Message, dept_name: str) -> None:
    """Fetch and send all PDFs for the given department to the admin."""
    reports = await get_reports_by_department(dept_name)

    if not reports:
        await target.answer(
            f"لا توجد تقارير مسلّمة بعد لقسم {dept_name}.",
            parse_mode="Markdown",
        )
        return

    await target.answer(
        f"*تقارير قسم {dept_name}*\nالعدد الكلي: *{len(reports)}*",
        parse_mode="Markdown",
    )

    for idx, report in enumerate(reports, start=1):
        caption = (
            f"تقرير رقم {idx}\n"
            f"الاسم: {report['full_name']}\n"
            f"وقت التسليم: {fmt_time_str(report['submission_time'])}"
        )
        try:
            await target.bot.send_document(  # type: ignore[union-attr]
                chat_id=target.chat.id,
                document=report["file_id"],
                caption=caption,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error(
                "Failed to send report #%s (%s) to admin: %s",
                idx, report["full_name"], exc,
            )
            # Fallback to text message
            fallback_text = (
                f"{caption}\n"
                f"(ملاحظة: تعذر إرسال الملف المرفق)"
            )
            await target.bot.send_message(  # type: ignore[union-attr]
                chat_id=target.chat.id,
                text=fallback_text,
                parse_mode="Markdown",
            )


# ──────────────────────────────────────────────
# CALLBACK: admin_stats
# ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return
    await _deliver_stats(callback.message)  # type: ignore[arg-type]
    await callback.answer(text="تم تحديث وعرض الإحصائيات")


# ──────────────────────────────────────────────
# CALLBACK: admin_view_depts
# ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_view_depts")
async def cb_admin_view_depts(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return
    await callback.message.answer(  # type: ignore[union-attr]
        "اختر القسم الذي تريد استعراض تقاريره:",
        reply_markup=admin_departments_reply_keyboard(),
    )
    await callback.answer(text="تم فتح قائمة الأقسام")


# ──────────────────────────────────────────────
# CALLBACK: admin_view_all
# ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_view_all")
async def cb_admin_view_all(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return
    await _deliver_all_reports(callback.message)  # type: ignore[arg-type]
    await callback.answer(text="جاري استعراض جميع ملفات الطلاب")


# ──────────────────────────────────────────────
# CALLBACK: view_{dept_callback}
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("view_dept_"))
async def cb_view_department_reports(callback: CallbackQuery) -> None:
    """Send all PDFs for the chosen department."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return

    dept_callback = callback.data[len("view_"):]       # strip 'view_' prefix → e.g. 'dept_ais'
    dept_name     = ALL_DEPARTMENTS.get(dept_callback)

    if not dept_name:
        await callback.answer("قسم غير معروف.", show_alert=True)
        return

    reports = await get_reports_by_department(dept_name)

    if not reports:
        await callback.message.answer(  # type: ignore[union-attr]
            f"لا توجد تقارير مسلّمة بعد لقسم {dept_name}.",
            parse_mode="Markdown",
        )
        await callback.answer(text=f"لا توجد تقارير لقسم {dept_name}")
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"تقارير قسم {dept_name}\nالعدد الكلي: *{len(reports)}*",
        parse_mode="Markdown",
    )

    for idx, report in enumerate(reports, start=1):
        caption = (
            f"تقرير رقم {idx}\n"
            f"الاسم: {report['full_name']}\n"
            f"وقت التسليم: {fmt_time_str(report['submission_time'])}"
        )
        try:
            await callback.message.bot.send_document(  # type: ignore[union-attr]
                chat_id=callback.from_user.id,
                document=report["file_id"],
                caption=caption,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error(
                "Failed to send report #%s (%s) to admin: %s",
                idx, report["full_name"], exc,
            )
            # Fallback to text message
            fallback_text = (
                f"{caption}\n"
                f"(ملاحظة: تعذر إرسال الملف المرفق)"
            )
            await callback.message.bot.send_message(  # type: ignore[union-attr]
                chat_id=callback.from_user.id,
                text=fallback_text,
                parse_mode="Markdown",
            )

    await callback.answer(text=f"تم جلب تقارير قسم {dept_name}")


# ──────────────────────────────────────────────
# CALLBACK: admin_back
# ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("غير مسموح.", show_alert=True)
        return
    await callback.message.answer(  # type: ignore[union-attr]
        "القائمة الرئيسية:",
        reply_markup=admin_reply_keyboard(),
    )
    await _send_admin_panel(callback.message)  # type: ignore[arg-type]
    await callback.answer(text="العودة للقائمة الرئيسية")
