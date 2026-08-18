"""Unique identifier helpers for auditable entities."""

from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    if not prefix or not prefix.strip():
        raise ValueError("id prefix is required")
    return f"{prefix}_{uuid4().hex}"


def new_signal_id() -> str:
    return new_id("sig")


def new_decision_id() -> str:
    return new_id("dec")


def new_order_id() -> str:
    return new_id("ord")


def new_position_id() -> str:
    return new_id("pos")


def new_event_id() -> str:
    return new_id("evt")

