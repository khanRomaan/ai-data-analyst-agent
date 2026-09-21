"""Stage 4: Visualization. Turns an analysis result into a chart image."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from intent_parser import Intent


def make_chart(result: dict, out_path: str) -> str | None:
    chart_type = result.get("chart_type")
    table = result["table"]
    intent: Intent = result["intent"]

    if chart_type is None or table.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))

    if chart_type == "bar":
        x_col, y_col = table.columns[0], table.columns[1]
        bars = ax.bar(table[x_col].astype(str), table[y_col], color="#4C72B0")
        ax.set_xlabel(x_col.replace("_", " ").title())
        ax.set_ylabel(y_col.replace("_", " ").title())
        ax.set_title(f"{intent.analysis_type.replace('_', ' ').title()}: {y_col} by {x_col} ({result['period_label']})")
        plt.xticks(rotation=30, ha="right")
        for b in bars:
            h = b.get_height()
            ax.annotate(f"{h:,.0f}", (b.get_x() + b.get_width() / 2, h), ha="center", va="bottom", fontsize=8)

    elif chart_type == "line":
        x_col, y_col = table.columns[0], table.columns[1]
        ax.plot(table[x_col], table[y_col], marker="o", color="#DD8452")
        ax.set_xlabel(x_col.replace("_", " ").title())
        ax.set_ylabel(y_col.replace("_", " ").title())
        ax.set_title(f"{y_col} over time")
        plt.xticks(rotation=30, ha="right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
