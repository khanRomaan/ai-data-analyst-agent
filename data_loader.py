"""Stage 1: Data Understanding.

Loads a CSV/Excel file and builds a structured profile of it: column types,
date ranges, categorical values, numeric summary stats. This profile is what
lets later stages (intent parsing, analysis, explanation) reason about the
data without re-scanning the raw file every time.
"""
from __future__ import annotations

import pandas as pd


def load_data(path: str) -> pd.DataFrame:
    """Loads a CSV or Excel file into a DataFrame, with light auto-cleaning."""
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    df.columns = [c.strip() for c in df.columns]

    # Best-effort auto-detection of date columns by name and by parseability
    for col in df.columns:
        is_text = df[col].dtype == object or pd.api.types.is_string_dtype(df[col])
        if is_text:
            name_hint = any(k in col.lower() for k in ["date", "time", "quarter", "month", "year"])
            if name_hint:
                parsed = pd.to_datetime(df[col], errors="coerce")
                # only convert if the majority actually parsed
                if parsed.notna().mean() > 0.8:
                    df[col] = parsed
    return df


def profile_data(df: pd.DataFrame) -> dict:
    """Builds a structured profile: schema, types, ranges. This is the
    'data understanding' the agent uses to decide how to analyze a question."""
    profile = {
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "columns": {},
        "date_columns": [],
        "numeric_columns": [],
        "categorical_columns": [],
        "id_columns": [],
    }

    for col in df.columns:
        series = df[col]
        col_info = {"dtype": str(series.dtype), "n_missing": int(series.isna().sum())}

        if pd.api.types.is_datetime64_any_dtype(series):
            col_info["min"] = str(series.min())
            col_info["max"] = str(series.max())
            profile["date_columns"].append(col)

        elif pd.api.types.is_numeric_dtype(series):
            col_info["min"] = float(series.min())
            col_info["max"] = float(series.max())
            col_info["mean"] = float(series.mean())
            profile["numeric_columns"].append(col)

        else:
            n_unique = series.nunique()
            col_info["n_unique"] = int(n_unique)
            looks_like_id = n_unique > 0.9 * len(series) and len(series) > 20
            if looks_like_id:
                profile["id_columns"].append(col)
            else:
                col_info["top_values"] = series.value_counts().head(8).to_dict()
                profile["categorical_columns"].append(col)

        profile["columns"][col] = col_info

    return profile


def profile_summary_text(profile: dict) -> str:
    """Human/LLM-readable summary of the data profile."""
    lines = [f"Dataset: {profile['n_rows']:,} rows, {profile['n_cols']} columns."]
    if profile["date_columns"]:
        for c in profile["date_columns"]:
            info = profile["columns"][c]
            lines.append(f"  Date column '{c}': spans {info['min']} to {info['max']}")
    if profile["numeric_columns"]:
        lines.append(f"  Numeric columns: {', '.join(profile['numeric_columns'])}")
    if profile["categorical_columns"]:
        cats = ", ".join(
            f"{c} ({profile['columns'][c]['n_unique']} unique)" for c in profile["categorical_columns"]
        )
        lines.append(f"  Categorical columns: {cats}")
    if profile["id_columns"]:
        lines.append(f"  ID-like columns: {', '.join(profile['id_columns'])}")
    return "\n".join(lines)
