"""
handlers/
---------
Package init — imports all handler routers so main.py can register them easily.
"""

from handlers.student import router as student_router
from handlers.admin import router as admin_router
from handlers.superadmin import router as superadmin_router

__all__ = ["student_router", "admin_router", "superadmin_router"]
