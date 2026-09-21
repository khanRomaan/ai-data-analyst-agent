"""AI Data Analyst Agent — orchestrator.

Pipeline: Question -> Data understanding -> Analysis (pandas) -> Visualization -> Explanation

Usage:
    from agent import DataAnalystAgent
    agent = DataAnalystAgent("sample_sales_data.csv")
    response = agent.ask("What were our top 5 products last quarter?")
    print(response.explanation)
    response.table          # pandas DataFrame of the result
    response.chart_path     # path to a saved PNG chart, if applicable
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from analyzer import AnalysisError, run_analysis
from data_loader import load_data, profile_data, profile_summary_text
from explainer import explain_result
from intent_parser import Intent, parse_question
from visualizer import make_chart


@dataclass
class AgentResponse:
    question: str
    explanation: str
    table: pd.DataFrame | None
    chart_path: str | None
    intent: Intent
    error: str | None = None


class DataAnalystAgent:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.df = load_data(data_path)
        self.profile = profile_data(self.df)

    def describe_data(self) -> str:
        return profile_summary_text(self.profile)

    def ask(self, question: str, chart_dir: str | None = None) -> AgentResponse:
        if chart_dir is None:
            chart_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
        intent = parse_question(question, self.profile)

        try:
            result = run_analysis(self.df, intent)
        except AnalysisError as e:
            return AgentResponse(
                question=question, explanation=f"I couldn't complete that analysis: {e}",
                table=None, chart_path=None, intent=intent, error=str(e),
            )

        os.makedirs(chart_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() else "_" for c in question)[:60]
        chart_path = os.path.join(chart_dir, f"{safe_name}.png")
        actual_chart_path = make_chart(result, chart_path)

        explanation = explain_result(result)

        return AgentResponse(
            question=question,
            explanation=explanation,
            table=result["table"],
            chart_path=actual_chart_path,
            intent=intent,
        )


if __name__ == "__main__":
    agent = DataAnalystAgent("sample_sales_data.csv")
    print(agent.describe_data())
    print()
    resp = agent.ask("What were our top 5 products last quarter?")
    print(resp.explanation)
    print()
    print(resp.table)
    print("Chart saved to:", resp.chart_path)
