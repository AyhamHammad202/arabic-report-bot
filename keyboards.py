"""
keyboards.py
------------
All Inline & Reply keyboard builders used throughout the bot.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import ALL_DEPARTMENTS, DEPARTMENTS


# ──────────────────────────────────────────────
# Student Flow Keyboards
# ──────────────────────────────────────────────

def college_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard to choose between the two colleges."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="كلية التميز",               callback_data="college_excellence"),
        InlineKeyboardButton(text="كلية الذكاء الاصطناعي",  callback_data="college_ai"),
    )
    return builder.as_markup()


def department_keyboard(college_callback: str) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard with the departments of the selected college.

    :param college_callback: e.g. 'college_excellence' or 'college_ai'
    """
    builder = InlineKeyboardBuilder()
    departments = DEPARTMENTS.get(college_callback, {})
    for callback_data, label in departments.items():
        builder.row(InlineKeyboardButton(text=label, callback_data=callback_data))
    return builder.as_markup()


# ──────────────────────────────────────────────
# Admin Panel — Persistent Reply Keyboard
# (always visible at the bottom of the screen)
# ──────────────────────────────────────────────

def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Persistent bottom keyboard for the admin.
    Always visible so the doctor never needs to type a command.
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="الإحصائيات"),
        KeyboardButton(text="ملفات الأقسام"),
    )
    builder.row(
        KeyboardButton(text="جميع ملفات الطلاب"),
        KeyboardButton(text="القائمة الرئيسية"),
    )
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove any persistent reply keyboard (used for students)."""
    return ReplyKeyboardRemove()


# ──────────────────────────────────────────────
# Admin Panel — Inline Keyboards
# ──────────────────────────────────────────────

def admin_main_inline_keyboard() -> InlineKeyboardMarkup:
    """Main admin panel inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="عرض الإحصائيات العامة",    callback_data="admin_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="استعراض ملفات الأقسام",    callback_data="admin_view_depts"),
    )
    builder.row(
        InlineKeyboardButton(text="عرض جميع ملفات الطلاب",   callback_data="admin_view_all"),
    )
    return builder.as_markup()


def admin_departments_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Reply keyboard showing all departments as tappable buttons,
    grouped by college with a back button at the bottom.
    """
    builder = ReplyKeyboardBuilder()

    # ── كلية التميز ──
    builder.row(KeyboardButton(text="كلية التميز"))          # section header (non-functional label)
    builder.row(
        KeyboardButton(text="نظم المعلومات التطبيقية"),
        KeyboardButton(text="علم البيانات"),
    )
    builder.row(
        KeyboardButton(text="الفلسفة وعلم الاجتماع"),
        KeyboardButton(text="المحاسبة والمصارف"),
    )
    builder.row(
        KeyboardButton(text="إدارة الأعمال والتجارة الإلكترونية"),
    )

    # ── كلية الذكاء الاصطناعي ──
    builder.row(KeyboardButton(text="كلية الذكاء الاصطناعي"))  # section header
    builder.row(
        KeyboardButton(text="التطبيقات الهندسية"),
        KeyboardButton(text="البيانات الضخمة"),
    )
    builder.row(
        KeyboardButton(text="التطبيقات الطبية الحيوية"),
    )

    # ── Back ──
    builder.row(KeyboardButton(text="رجوع للقائمة الرئيسية"))

    return builder.as_markup(resize_keyboard=True, is_persistent=True)


# Flat set of all department names for fast lookup in the message handler
ALL_DEPT_NAMES: set[str] = set(ALL_DEPARTMENTS.values())

# Keep old name as alias so existing imports still resolve
admin_main_keyboard = admin_main_inline_keyboard
admin_departments_keyboard = admin_departments_reply_keyboard


# ──────────────────────────────────────────────
# Superadmin Keyboards
# ──────────────────────────────────────────────

def superadmin_main_keyboard() -> InlineKeyboardMarkup:
    """Main superadmin panel inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="حذف تقرير طالب",       callback_data="sa_delete_one"),
    )
    builder.row(
        InlineKeyboardButton(text="حذف جميع التقارير",      callback_data="sa_delete_all_ask"),
    )
    builder.row(
        InlineKeyboardButton(text="عرض قائمة الطلاب",      callback_data="sa_list_students"),
    )
    return builder.as_markup()


def students_delete_keyboard(students: list[dict]) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard listing every student as a deletable row.
    Each button shows:  اسم الطالب | القسم
    Callback: sa_del_ask_{submission_id}
    """
    builder = InlineKeyboardBuilder()
    for student in students:
        label = f"{student['full_name']}  —  {student['department']}"
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"sa_del_ask_{student['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="إلغاء", callback_data="sa_cancel")
    )
    return builder.as_markup()


def students_list_keyboard(students: list[dict]) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard listing every student for the view-details flow.
    Each button shows:  اسم الطالب — القسم
    Callback: sa_view_{submission_id}
    """
    builder = InlineKeyboardBuilder()
    for student in students:
        label = f"{student['full_name']}  —  {student['department']}"
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"sa_view_{student['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="إلغاء", callback_data="sa_cancel")
    )
    return builder.as_markup()


def delete_confirm_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """Two-button confirmation keyboard: confirm or cancel deletion."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="نعم، احذف التقرير",
            callback_data=f"sa_del_exec_{submission_id}",
        ),
        InlineKeyboardButton(
            text="إلغاء",
            callback_data="sa_cancel",
        ),
    )
    return builder.as_markup()


def delete_all_confirm_keyboard() -> InlineKeyboardMarkup:
    """Two-button confirmation for wiping ALL submissions."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="نعم، احذف الكل",
            callback_data="sa_delete_all_exec",
        ),
        InlineKeyboardButton(
            text="إلغاء",
            callback_data="sa_cancel",
        ),
    )
    return builder.as_markup()
