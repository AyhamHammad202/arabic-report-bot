"""
states.py
---------
FSM (Finite State Machine) state groups for the student submission flow.
"""

from aiogram.fsm.state import State, StatesGroup


class ReportForm(StatesGroup):
    """States for the student report submission flow."""
    awaiting_name       = State()   # Waiting for the student to type their full name
    awaiting_college    = State()   # Waiting for college selection via inline keyboard
    awaiting_department = State()   # Waiting for department selection via inline keyboard
    awaiting_report     = State()   # Waiting for the student to upload a PDF file
