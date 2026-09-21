"""Stage 3: Analysis. Executes the parsed Intent as pandas operations.

This is the "Python/SQL" step from the spec. Rather than having an LLM
generate ad-hoc code (slower, harder to sandbox/trust), we run a fixed
library of deterministic, tested pandas operations parameterized by the
Intent. This is safer and reproducible for a v1; the same Intent interface
could later dispatch to LLM-generated SQL/pandas for open-ended questions.
"""
from __future__ import annotations

import pandas as pd

from intent_parser import Intent


class AnalysisError(Exception):
    pass


def _apply_time_filter(df: pd.DataFrame, intent: Intent) -> tuple[pd.DataFrame, str]:
    """Filters df to the requested time window, relative to the max date
    present in the data (not wall-clock 'today') since analysts usually mean
    'relative to the data', especially for extracts that aren't live."""
    if not intent.time_col or intent.time_filter in (None, "all"):
        if intent.time_filter not in (None, "all") and not intent.time_col:
            return df, "all available data (no date column found, so the time period you asked for was ignored)"
        return df, "all available data"

    max_date = df[intent.time_col].max()
    label = "all available data"

    if intent.time_filter in ("last_quarter", "current_quarter"):
        period = df[intent.time_col].dt.to_period("Q")
        current_q = max_date.to_period("Q")
        target_q = current_q if intent.time_filter == "current_quarter" else current_q - 1
        mask = period == target_q
        label = f"{target_q} ({target_q.start_time.date()} to {target_q.end_time.date()})"
        return df[mask], label

    if intent.time_filter == "last_month":
        period = df[intent.time_col].dt.to_period("M")
        target_m = max_date.to_period("M") - 1
        mask = period == target_m
        label = f"{target_m}"
        return df[mask], label

    if intent.time_filter == "last_year":
        target_y = max_date.year - 1
        mask = df[intent.time_col].dt.year == target_y
        label = f"{target_y}"
        return df[mask], label

    if intent.time_filter == "ytd":
        mask = df[intent.time_col].dt.year == max_date.year
        label = f"year-to-date {max_date.year}"
        return df[mask], label

    return df, label


def run_analysis(df: pd.DataFrame, intent: Intent) -> dict:
    """Executes the intent. Returns a result dict with a result DataFrame
    plus metadata used by the visualizer and explainer."""
    filtered, period_label = _apply_time_filter(df, intent)

    if len(filtered) == 0:
        raise AnalysisError(
            f"No rows found for the requested period ({period_label}). "
            f"Data covers {df[intent.time_col].min().date()} to {df[intent.time_col].max().date()}."
            if intent.time_col else "No rows found."
        )

    if not intent.metric_col:
        raise AnalysisError("Could not identify a numeric metric column to analyze.")

    result: dict = {
        "intent": intent,
        "period_label": period_label,
        "n_rows_analyzed": len(filtered),
    }

    if intent.analysis_type == "top_n":
        if not intent.entity_col:
            raise AnalysisError("Could not identify a category column (e.g. product) to rank by.")
        grouped = (
            filtered.groupby(intent.entity_col)[intent.metric_col]
            .sum()
            .sort_values(ascending="ascending" in intent.notes)
        )
        top = grouped.head(intent.n).reset_index()
        top.columns = [intent.entity_col, intent.metric_col]
        result["table"] = top
        result["chart_type"] = "bar"
        result["total_in_period"] = float(grouped.sum())

    elif intent.analysis_type == "trend":
        if not intent.time_col:
            raise AnalysisError(
                "This question needs a date/time column to show a trend, but I couldn't find one "
                "in your data. Try a question that doesn't need a time axis, like a top-N or comparison question."
            )
        freq = "ME" if (filtered[intent.time_col].max() - filtered[intent.time_col].min()).days > 60 else "D"
        series = (
            filtered.set_index(intent.time_col)[intent.metric_col]
            .resample(freq)
            .sum()
            .reset_index()
        )
        result["table"] = series
        result["chart_type"] = "line"

    elif intent.analysis_type == "comparison":
        group_col = intent.group_col or intent.entity_col
        if not group_col:
            raise AnalysisError("Could not identify columns to compare.")
        grouped = filtered.groupby(group_col)[intent.metric_col].sum().sort_values(ascending=False).reset_index()
        result["table"] = grouped
        result["chart_type"] = "bar"

    else:  # summary
        summary = {
            "total": float(filtered[intent.metric_col].sum()),
            "mean": float(filtered[intent.metric_col].mean()),
            "count": int(len(filtered)),
        }
        result["table"] = pd.DataFrame([summary])
        result["chart_type"] = None

    return result
