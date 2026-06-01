"""
config.py
---------
Loads and validates all environment variables and global constants.
"""

import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ----- Bot Credentials -----
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to your .env file.")

ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
if not ADMIN_ID:
    raise ValueError("ADMIN_ID is not set. Please add it to your .env file.")

SUPER_ADMIN_ID: int = int(os.getenv("SUPER_ADMIN_ID", "0"))
if not SUPER_ADMIN_ID:
    raise ValueError("SUPER_ADMIN_ID is not set. Please add it to your .env file.")


# ----- Firebase -----
# The full service-account JSON is stored in this env variable.
# For local dev you can point to a file path instead (see .env.example).
FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "")
FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

# ----- College & Department Mappings -----
# Maps callback data -> Arabic display name
COLLEGES: dict[str, str] = {
    "college_excellence": "كلية التميز",
    "college_ai":         "كلية الذكاء الاصطناعي",
}

DEPARTMENTS: dict[str, dict[str, str]] = {
    "college_excellence": {
        "dept_ais":    "نظم المعلومات التطبيقية",
        "dept_ds":     "علم البيانات",
        "dept_phil":   "الفلسفة وعلم الاجتماع",
        "dept_acc":    "المحاسبة والمصارف",
        "dept_biz":    "إدارة الأعمال والتجارة الإلكترونية",
    },
    "college_ai": {
        "dept_eng":     "التطبيقات الهندسية",
        "dept_bigdata": "البيانات الضخمة",
        "dept_bio":     "التطبيقات الطبية الحيوية",
    },
}

# Flat map: callback -> Arabic name (for quick lookups)
ALL_DEPARTMENTS: dict[str, str] = {
    k: v
    for college_depts in DEPARTMENTS.values()
    for k, v in college_depts.items()
}
