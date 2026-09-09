"""Server-side case helpers for the LINE -> manual CYBOW entry workflow."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from src import db_handler

CASE_TTL_HOURS = 8


def create_manual_case(patient_name: str, line_user_id: str) -> str:
    name = (patient_name or "").strip()
    if not name:
        raise ValueError("patient_name is required")
    token = secrets.token_urlsafe(24)
    if not db_handler.create_manual_case(token, name, line_user_id or ""):
        raise RuntimeError("failed to create manual case")
    return token


def get_manual_case(token: str):
    token = (token or "").strip()
    if not token:
        return None
    case = db_handler.get_manual_case(token)
    if not case:
        return None
    created_at = case.get("created_at")
    if case.get("status") != "pending":
        return {**case, "valid": False, "reason": "case_not_pending"}
    if created_at and datetime.now(created_at.tzinfo) - created_at > timedelta(hours=CASE_TTL_HOURS):
        return {**case, "valid": False, "reason": "case_expired"}
    return {**case, "valid": True, "reason": None}


def complete_manual_case(token: str) -> bool:
    return db_handler.complete_manual_case((token or "").strip())
