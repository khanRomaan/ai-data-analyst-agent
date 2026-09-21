"""Stage 2: Question -> structured analysis intent.

Turns a natural-language question into a structured plan the analyzer can
execute deterministically in pandas. This version uses rule-based matching
(keywords + column-name fuzzy matching) so the pipeline works with zero
external API calls. See llm_client.py for how this stage can be swapped
for an LLM call that returns the same structured intent as JSON.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import get_close_matches

import pandas as pd


@dataclass
class Intent:
    analysis_type: str  # "top_n" | "trend" | "comparison" | "summary"
    metric_col: str | None = None
    entity_col: str | None = None
    n: int = 5
    time_col: str | None = None
    time_filter: str | None = None  # e.g. "last_quarter", "last_month", "last_year", "all"
    group_col: str | None = None  # secondary grouping, for comparisons
    raw_question: str = ""
    notes: list = field(default_factory=list)


_METRIC_HINTS = ["revenue", "sales", "profit", "amount", "total", "price", "income"]
_QTY_HINTS = ["quantity", "units", "count", "volume"]
_ENTITY_HINTS = ["product", "item", "sku", "category"]


def _best_match(hints: list[str], columns: list[str]) -> str | None:
    for hint in hints:
        for col in columns:
            if hint in col.lower():
                return col
    matches = get_close_matches(hints[0], [c.lower() for c in columns], n=1, cutoff=0.6)
    if matches:
        return next(c for c in columns if c.lower() == matches[0])
    return None


def parse_question(question: str, profile: dict) -> Intent:
    q = question.lower()
    columns = list(profile["columns"].keys())
    numeric_cols = profile["numeric_columns"]
    cat_cols = profile["categorical_columns"]
    date_cols = profile["date_columns"]

    intent = Intent(analysis_type="summary", raw_question=question)

    # --- time filter ---
    intent.time_col = date_cols[0] if date_cols else None
    if "last quarter" in q or "past quarter" in q:
        intent.time_filter = "last_quarter"
    elif "this quarter" in q or "current quarter" in q:
        intent.time_filter = "current_quarter"
    elif "last month" in q:
        intent.time_filter = "last_month"
    elif "last year" in q or "past year" in q:
        intent.time_filter = "last_year"
    elif "year to date" in q or "ytd" in q:
        intent.time_filter = "ytd"
    else:
        intent.time_filter = "all"

    # --- analysis type ---
    n_match = re.search(r"(?:top|bottom)\s+(\d+)", q)
    top_words = ("top", "best", "highest", "most")
    bottom_words = ("bottom", "worst", "lowest", "least")
    if n_match or any(w in q for w in top_words) or any(w in q for w in bottom_words):
        intent.analysis_type = "top_n"
        intent.n = int(n_match.group(1)) if n_match else 5
        if any(w in q for w in bottom_words):
            intent.notes.append("ascending")
    elif any(w in q for w in ["trend", "over time", "growth", "monthly", "weekly", "daily"]):
        intent.analysis_type = "trend"
    elif any(w in q for w in ["compare", "vs", "versus", "difference between"]):
        intent.analysis_type = "comparison"
    else:
        intent.analysis_type = "summary"

    # --- metric column (what to measure) ---
    if any(w in q for w in _QTY_HINTS) and not any(w in q for w in _METRIC_HINTS):
        intent.metric_col = _best_match(_QTY_HINTS, numeric_cols) or (numeric_cols[0] if numeric_cols else None)
    else:
        intent.metric_col = _best_match(_METRIC_HINTS, numeric_cols) or (numeric_cols[0] if numeric_cols else None)

    # --- entity column (what to group by) ---
    # Prefer a column name the user actually said (e.g. "by category") over
    # generic hint words, so "top categories" doesn't default to "product".
    intent.entity_col = None
    for col in cat_cols:
        label = col.lower().replace("_", " ")
        candidates = {label, label + "s", label + "es"}
        if label.endswith("y"):
            candidates.add(label[:-1] + "ies")
        if any(re.search(rf"\b{re.escape(c)}\b", q) for c in candidates):
            intent.entity_col = col
            break
    if intent.entity_col is None:
        intent.entity_col = _best_match(_ENTITY_HINTS, cat_cols)
    if intent.entity_col is None and cat_cols:
        intent.entity_col = cat_cols[0]

    # --- secondary group column, for comparison-style questions ---
    for col in cat_cols:
        label = col.lower().replace("_", " ")
        if label in q and col != intent.entity_col:
            intent.group_col = col
            break

    return intent
