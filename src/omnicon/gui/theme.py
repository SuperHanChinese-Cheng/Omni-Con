# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Centralized theme helpers — palette-aware colors for light and dark mode."""

from PySide6.QtWidgets import QApplication


def is_dark_mode() -> bool:
    """Return True if the app is running in dark mode."""
    app = QApplication.instance()
    if app is not None:
        return bool(app.property("_omnicon_dark"))
    return False


def drop_zone_idle() -> str:
    if is_dark_mode():
        return (
            "QLabel { border: 2px dashed #666; border-radius: 8px;"
            " background: #2d2d2d; color: #aaa; font-size: 13px; padding: 16px; }"
        )
    return (
        "QLabel { border: 2px dashed #888; border-radius: 8px;"
        " background: #f8f8f8; color: #888; font-size: 13px; padding: 16px; }"
    )


def drop_zone_hover() -> str:
    if is_dark_mode():
        return (
            "QLabel { border: 2px dashed #0078d4; border-radius: 8px;"
            " background: #1a3a5c; color: #5ba3d9; font-size: 13px; padding: 16px; }"
        )
    return (
        "QLabel { border: 2px dashed #0078d4; border-radius: 8px;"
        " background: #e8f0fe; color: #0078d4; font-size: 13px; padding: 16px; }"
    )


def drop_zone_loaded() -> str:
    if is_dark_mode():
        return (
            "QLabel { border: 2px solid #107c10; border-radius: 8px;"
            " background: #1a3d1a; color: #5cb85c; font-size: 13px; padding: 16px; }"
        )
    return (
        "QLabel { border: 2px solid #107c10; border-radius: 8px;"
        " background: #f0fff0; color: #107c10; font-size: 13px; padding: 16px; }"
    )


def btn_primary() -> str:
    return (
        "QPushButton { background: #0078d4; color: white; font-size: 14px;"
        " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
        "QPushButton:disabled { background: #555; }" if is_dark_mode() else
        "QPushButton { background: #0078d4; color: white; font-size: 14px;"
        " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
        "QPushButton:disabled { background: #ccc; }"
        "QPushButton:hover:!disabled { background: #106ebe; }"
    )


def btn_build() -> str:
    return (
        "QPushButton { background: #107c10; color: white; font-size: 15px;"
        " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
        "QPushButton:hover { background: #0b6a0b; }"
    )


def btn_tool() -> str:
    if is_dark_mode():
        return (
            "QPushButton { background: #3d3d3d; color: #ddd; padding: 6px 14px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #505050; }"
        )
    return (
        "QPushButton { background: #e8e8e8; padding: 6px 14px;"
        " border-radius: 4px; font-weight: bold; }"
        "QPushButton:hover { background: #d0d0d0; }"
    )


def btn_remove() -> str:
    return (
        "QPushButton { background: #d13438; color: white; font-weight: bold;"
        " border-radius: 4px; } QPushButton:hover { background: #a4262c; }"
    )


def file_row() -> str:
    if is_dark_mode():
        return (
            "QWidget { background: #2d2d2d; border: 1px solid #444;"
            " border-radius: 4px; }"
        )
    return (
        "QWidget { background: #fafafa; border: 1px solid #e0e0e0;"
        " border-radius: 4px; }"
    )


def label_muted() -> str:
    return "color: #aaa; font-size: 11px;" if is_dark_mode() else "color: #666; font-size: 11px;"


def label_accent() -> str:
    return "color: #5ba3d9; font-size: 12px;" if is_dark_mode() else "color: #0078d4; font-size: 12px;"


def label_hint() -> str:
    return "color: #999; font-size: 11px;" if is_dark_mode() else "color: #888; font-size: 11px;"


def label_queue_title() -> str:
    return "font-weight: bold; font-size: 13px;"


def status_done() -> str:
    return "color: #5cb85c;" if is_dark_mode() else "color: #107c10;"


def status_failed() -> str:
    return "color: #f44747;" if is_dark_mode() else "color: #d13438;"


def update_banner() -> str:
    if is_dark_mode():
        return (
            "QFrame { background: #1a3a5c; border: 1px solid #2d5f8a;"
            " border-radius: 6px; padding: 6px 12px; }"
        )
    return (
        "QFrame { background: #e8f4fd; border: 1px solid #b3d9f2;"
        " border-radius: 6px; padding: 6px 12px; }"
    )


def update_banner_text() -> str:
    return "color: #7db8e0; font-size: 12px;" if is_dark_mode() else "color: #0b5394; font-size: 12px;"


def update_banner_dismiss() -> str:
    if is_dark_mode():
        return (
            "QPushButton { background: transparent; color: #7db8e0;"
            " border: 1px solid #7db8e0; border-radius: 4px;"
            " padding: 2px 10px; font-size: 11px; }"
            "QPushButton:hover { background: #2d5f8a; }"
        )
    return (
        "QPushButton { background: transparent; color: #0b5394;"
        " border: 1px solid #0b5394; border-radius: 4px;"
        " padding: 2px 10px; font-size: 11px; }"
        "QPushButton:hover { background: #d0e8f7; }"
    )
