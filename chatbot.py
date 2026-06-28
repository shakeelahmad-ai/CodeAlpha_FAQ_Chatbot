from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

from config import (
    FAQ_CSV_PATH,
    FALLBACK_RESPONSE,
    GREETING_MESSAGES,
    SIMILARITY_HIGH,
    SIMILARITY_MEDIUM,
    get_confidence_label,
)
from utils import normalize_text


STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "i", "me", "my", "myself", "we", "our", "ours",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
    "it", "its", "they", "them", "their", "theirs", "what", "which",
    "who", "whom", "this", "that", "these", "those", "and", "but", "if",
    "or", "because", "as", "until", "while", "how", "when", "where",
    "why", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "not", "only", "same", "so", "than", "too", "very",
    "just", "about", "get", "give", "go", "make", "know", "think", "see",
    "come", "want", "look", "use", "find", "tell", "ask", "seem", "feel",
    "try", "leave", "call", "keep", "let", "begin", "show", "hear",
    "play", "run", "move", "live", "believe", "hold", "bring", "happen",
    "write", "sit", "stand", "lose", "pay", "meet", "include", "continue",
    "set", "learn", "change", "lead", "understand", "watch", "follow",
    "stop", "create", "speak", "read", "spend", "grow", "open", "walk",
    "win", "offer", "remember", "love", "consider", "appear", "buy",
    "wait", "serve", "send", "expect", "build", "stay", "fall", "cut",
    "reach", "kill", "remain", "suggest", "raise", "pass", "across",
    "put", "end", "turn", "next", "even", "new", "old", "first", "last",
    "long", "great", "little", "own", "right", "big", "high", "different",
    "small", "large", "next", "early", "young", "important", "public",
    "private", "real", "best", "free", "able", "sure", "good", "must",
}


def _meaningful_words(text: str) -> set[str]:
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return {w for w in words if w not in STOPWORDS}


@dataclass
class FAQEntry:
    question:   str
    answer:     str
    category:   str = "General"
    normalized: str = field(init=False, repr=False)
    keywords:   set[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.normalized = normalize_text(self.question)
        self.keywords   = _meaningful_words(self.normalized)


@dataclass
class MatchResult:
    answer:           str
    score:            float
    matched_question: str | None = None
    category:         str        = "General"
    is_fallback:      bool       = False
    label:            str        = ""
    emoji:            str        = ""

    def __post_init__(self) -> None:
        lbl, emo    = get_confidence_label(self.score)
        self.label  = lbl
        self.emoji  = emo


class FAQEngine:

    def __init__(self, csv_path: str = FAQ_CSV_PATH) -> None:
        self._csv_path       = csv_path
        self._entries:       list[FAQEntry] = []
        self._norm_questions: list[str]     = []
        self._raw_questions:  list[str]     = []
        self._loaded         = False
        self._load_faq()

    def _load_faq(self) -> None:
        path = Path(self._csv_path)
        if not path.exists():
            raise FileNotFoundError(
                f"FAQ file not found: {self._csv_path}\n"
                "Ensure faq.csv exists in the project root."
            )

        self._entries.clear()
        self._norm_questions.clear()
        self._raw_questions.clear()

        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = row.get("question", "").strip()
                answer   = row.get("answer",   "").strip()
                category = row.get("category", "General").strip()
                if not question or not answer:
                    continue
                entry = FAQEntry(question=question, answer=answer, category=category)
                self._entries.append(entry)
                self._norm_questions.append(entry.normalized)
                self._raw_questions.append(entry.question)

        self._loaded = True

    def reload(self) -> None:
        self._load_faq()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def raw_questions(self) -> list[str]:
        return list(self._raw_questions)

    @property
    def categories(self) -> list[str]:
        seen: dict[str, None] = {}
        for e in self._entries:
            seen[e.category] = None
        return list(seen.keys())

    def get_entries_by_category(self, category: str) -> list[FAQEntry]:
        return [e for e in self._entries if e.category == category]

    def get_all_entries(self) -> list[dict[str, str]]:
        return [
            {"question": e.question, "answer": e.answer, "category": e.category}
            for e in self._entries
        ]

    def match(self, user_input: str) -> MatchResult:
        if not user_input or not user_input.strip():
            return MatchResult(answer=FALLBACK_RESPONSE, score=0.0, is_fallback=True)

        if not self._loaded or not self._entries:
            return MatchResult(
                answer="The FAQ database is not loaded. Please restart the app.",
                score=0.0, is_fallback=True,
            )

        normalised_input = normalize_text(user_input)
        query_keywords   = _meaningful_words(normalised_input)
        query_word_count = len(normalised_input.split())

        for entry in self._entries:
            if entry.normalized == normalised_input:
                return MatchResult(
                    answer=entry.answer,
                    score=100.0,
                    matched_question=entry.question,
                    category=entry.category,
                    is_fallback=False,
                )

        wr_result = process.extractOne(
            normalised_input,
            self._norm_questions,
            scorer=fuzz.WRatio,
            score_cutoff=0,
        )

        if wr_result is None:
            return MatchResult(answer=FALLBACK_RESPONSE, score=0.0, is_fallback=True)

        best_norm_q, best_score, best_idx = wr_result
        entry = self._entries[best_idx]

        if query_keywords:
            overlap = query_keywords & entry.keywords
            if len(overlap) == 0:
                return MatchResult(
                    answer=FALLBACK_RESPONSE,
                    score=best_score,
                    matched_question=None,
                    category="N/A",
                    is_fallback=True,
                )

        if query_word_count <= 2 and best_score < 85:
            return MatchResult(
                answer=FALLBACK_RESPONSE,
                score=best_score,
                matched_question=None,
                category="N/A",
                is_fallback=True,
            )

        if best_score >= SIMILARITY_HIGH:
            return MatchResult(
                answer=entry.answer,
                score=best_score,
                matched_question=entry.question,
                category=entry.category,
                is_fallback=False,
            )

        if best_score >= SIMILARITY_MEDIUM:
            close_answer = (
                f"Based on your question, here's the closest answer I found:\n\n"
                f"{entry.answer}"
            )
            return MatchResult(
                answer=close_answer,
                score=best_score,
                matched_question=entry.question,
                category=entry.category,
                is_fallback=False,
            )

        return MatchResult(
            answer=FALLBACK_RESPONSE,
            score=best_score,
            matched_question=None,
            category="N/A",
            is_fallback=True,
        )

    @staticmethod
    def greeting() -> str:
        return random.choice(GREETING_MESSAGES)

    def search_faq(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        normalised = normalize_text(query)
        results = process.extract(
            normalised,
            self._norm_questions,
            scorer=fuzz.WRatio,
            limit=limit,
        )

        output: list[dict[str, Any]] = []
        for _, score, idx in results:
            if score < 35:
                continue
            entry = self._entries[idx]
            output.append({
                "question": entry.question,
                "answer":   entry.answer,
                "category": entry.category,
                "score":    round(score, 1),
            })
        return output