"""Stage 5: Explanation. Turns structured analysis results into natural
language.

Per the chosen design, this stage does NOT execute LLM-generated code
against raw data (see analyzer.py for the deterministic execution layer).
Instead, it hands the LLM only the *already-computed* result table -
small, precise, and cheap - and asks it to narrate it. This is the
"reason over a data summary and answer directly" approach: accurate,
because the numbers come from real pandas aggregation, and fast, because
the LLM never sees the raw dataset.

call_llm() is a clean seam: wire it to a real Claude API call (see
llm_client.py) to get richer, more natural prose. Without an API key
configured, it falls back to a solid template-based explanation so the
pipeline works standalone.
"""
from __future__ import annotations

from intent_parser import Intent


def _template_explanation(result: dict) -> str:
    intent: Intent = result["intent"]
    table = result["table"]
    period = result["period_label"]

    if intent.analysis_type == "top_n":
        entity_col, metric_col = table.columns[0], table.columns[1]
        direction = "lowest" if "ascending" in intent.notes else "top"
        lines = [f"**{direction.title()} {len(table)} {entity_col} by {metric_col}** ({period}):", ""]
        for i, row in table.iterrows():
            share = (row[metric_col] / result["total_in_period"] * 100) if result.get("total_in_period") else None
            share_txt = f" ({share:.1f}% of total)" if share is not None else ""
            lines.append(f"{i+1}. **{row[entity_col]}** — {row[metric_col]:,.2f}{share_txt}")
        lines.append("")
        lines.append(
            f"Together these {len(table)} {entity_col.lower()}(s) account for "
            f"{table[metric_col].sum():,.2f} of {metric_col}, analyzed over {result['n_rows_analyzed']:,} rows."
        )
        return "\n".join(lines)

    if intent.analysis_type == "trend":
        y_col = table.columns[1]
        first, last = table.iloc[0][y_col], table.iloc[-1][y_col]
        change = ((last - first) / first * 100) if first else 0
        direction = "increased" if change >= 0 else "decreased"
        return (
            f"**Trend in {y_col}** over {period}: started at {first:,.2f}, ended at {last:,.2f} "
            f"— {direction} by {abs(change):.1f}% across the period, based on {len(table)} time buckets."
        )

    if intent.analysis_type == "comparison":
        x_col, y_col = table.columns[0], table.columns[1]
        best = table.iloc[0]
        lines = [f"**Comparison of {y_col} by {x_col}** ({period}):", ""]
        for _, row in table.iterrows():
            lines.append(f"- **{row[x_col]}**: {row[y_col]:,.2f}")
        lines.append("")
        lines.append(f"**{best[x_col]}** leads with {best[y_col]:,.2f}.")
        return "\n".join(lines)

    # summary
    row = table.iloc[0]
    return (
        f"Over {period}, total was **{row['total']:,.2f}** across {int(row['count']):,} records "
        f"(average {row['mean']:,.2f} per record)."
    )


def call_llm(prompt: str) -> str | None:
    """Seam for a real LLM call. Returns None if not configured, in which
    case explain_result() falls back to the template. Wire this to
    llm_client.ask_claude(prompt) to enable it."""
    return None


def explain_result(result: dict) -> str:
    llm_prompt = (
        "You are a data analyst. Explain this analysis result to a business "
        f"stakeholder in 2-4 sentences, in plain language.\n\nQuestion: {result['intent'].raw_question}\n"
        f"Period analyzed: {result['period_label']}\n"
        f"Result table:\n{result['table'].to_string(index=False)}"
    )
    llm_answer = call_llm(llm_prompt)
    if llm_answer:
        return llm_answer
    return _template_explanation(result)
