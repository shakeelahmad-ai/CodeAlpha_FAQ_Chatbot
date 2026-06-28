from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from config import (
    CHAT_HISTORY_PATH,
    DATA_DIR,
    EXPORT_FILENAME,
    HISTORY_JSON,
    MAX_HISTORY_ENTRIES,
)


def ensure_directories() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    for path in [CHAT_HISTORY_PATH, HISTORY_JSON]:
        p = Path(path)
        if not p.exists():
            p.write_text("[]", encoding="utf-8")


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def short_timestamp() -> str:
    return datetime.now().strftime("%I:%M %p")


def date_for_header() -> str:
    return datetime.now().strftime("%A, %d %B %Y")


def normalize_text(text: str) -> str:
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_history(filepath: str = HISTORY_JSON) -> list[dict[str, Any]]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(
    messages: list[dict[str, Any]],
    filepath: str = HISTORY_JSON,
) -> None:
    try:
        trimmed = messages[-MAX_HISTORY_ENTRIES:]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[utils] Warning: could not save history: {exc}")


def append_message(
    role: str,
    content: str,
    score: float | None = None,
    category: str | None = None,
    filepath: str = HISTORY_JSON,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "role":      role,
        "content":   content,
        "timestamp": now_timestamp(),
        "short_ts":  short_timestamp(),
    }
    if score is not None:
        entry["score"] = round(score, 1)
    if category is not None:
        entry["category"] = category

    history = load_history(filepath)
    history.append(entry)
    save_history(history, filepath)
    return entry


def clear_history(filepath: str = HISTORY_JSON) -> None:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([], f)
    except OSError as exc:
        print(f"[utils] Warning: could not clear history: {exc}")


def export_chat_as_txt(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return "No chat history to export."

    lines: list[str] = [
        "=" * 60,
        f"  AI FAQ CHATBOT — CHAT EXPORT",
        f"  Generated: {now_timestamp()}",
        "=" * 60,
        "",
    ]

    for msg in messages:
        role      = msg.get("role", "unknown").upper()
        content   = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        score     = msg.get("score")
        category  = msg.get("category")

        lines.append(f"[{timestamp}] {role}")
        lines.append(content)

        meta: list[str] = []
        if score is not None:
            meta.append(f"Confidence: {score:.1f}%")
        if category:
            meta.append(f"Category: {category}")
        if meta:
            lines.append(f"({' | '.join(meta)})")

        lines.append("-" * 40)
        lines.append("")

    lines += ["=" * 60, "End of Export", "=" * 60]
    return "\n".join(lines)


def compute_statistics(messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_msgs = [m for m in messages if m.get("role") == "user"]
    bot_msgs  = [m for m in messages if m.get("role") == "assistant"]

    scores     = [m["score"] for m in bot_msgs if "score" in m]
    categories = [m["category"] for m in bot_msgs if "category" in m]

    avg_confidence: float | None = (
        round(sum(scores) / len(scores), 1) if scores else None
    )

    cat_freq: dict[str, int] = {}
    for cat in categories:
        cat_freq[cat] = cat_freq.get(cat, 0) + 1
    top_categories = sorted(cat_freq.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_messages":    len(messages),
        "user_messages":     len(user_msgs),
        "bot_messages":      len(bot_msgs),
        "avg_confidence":    avg_confidence,
        "top_categories":    top_categories,
        "high_conf_count":   sum(1 for s in scores if s >= 75),
        "medium_conf_count": sum(1 for s in scores if 55 <= s < 75),
        "low_conf_count":    sum(1 for s in scores if s < 55),
    }


def filter_suggestions(
    query: str,
    questions: list[str],
    max_results: int = 4,
) -> list[str]:
    if not query or len(query) < 3:
        return []
    q_lower = query.lower()
    return [q for q in questions if q_lower in q.lower()][:max_results]


def truncate(text: str, max_len: int = 80, ellipsis: str = "…") -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - len(ellipsis)] + ellipsis


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default