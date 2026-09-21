# AI Data Analyst Agent — v1 (Python core)

Implements the pipeline:
**Question → Data understanding → Analysis (pandas) → Visualization → Explanation**

## Files
- `data_loader.py` — loads CSV/Excel, auto-detects date/numeric/categorical columns, builds a data profile (Stage: Data Understanding)
- `intent_parser.py` — rule-based NL → structured `Intent` (analysis type, metric, entity, time window) (Stage: Question understanding)
- `analyzer.py` — executes the `Intent` as deterministic pandas groupby/resample operations (Stage: Analysis / "Python-SQL")
- `visualizer.py` — renders a bar or line chart from the result (Stage: Visualization)
- `explainer.py` — turns the result table into natural language; has a clean seam (`call_llm`) to plug in a real Claude API call (Stage: Explanation)
- `llm_client.py` — optional: wires `explainer.call_llm()` to the real Anthropic API
- `agent.py` — orchestrator: `DataAnalystAgent(path).ask(question)` runs the full pipeline
- `generate_sample_data.py` — builds `sample_sales_data.csv`, a 2-year synthetic sales dataset, for testing

## Quick start
```bash
python3 generate_sample_data.py   # only needed once, or bring your own CSV/Excel
python3 agent.py                  # runs the example question end-to-end
```

```python
from agent import DataAnalystAgent

agent = DataAnalystAgent("sample_sales_data.csv")
resp = agent.ask("What were our top 5 products last quarter?")

print(resp.explanation)   # natural-language answer
resp.table                # pandas DataFrame of the numbers
resp.chart_path           # PNG chart path (None if not applicable, e.g. plain summaries)
```

## Design decisions (per current scope)
- **No LLM-generated code execution.** The analyzer runs a fixed, tested library of pandas
  operations (top-N, trend, comparison, summary), parameterized by the parsed `Intent`. This is
  safer and fully reproducible for v1. The LLM (when wired via `llm_client.py`) only narrates
  the *already-computed* result table — it never touches raw data or writes code that executes
  against it.
- **"Last quarter" etc. are relative to the data's own max date**, not wall-clock today —
  correct behavior for historical extracts that may not be fully current.
- **Intent parsing is rule-based** (keyword + column-name matching), so the whole pipeline runs
  with zero API calls / zero cost. It correctly handles top-N (incl. "bottom N"), trends,
  comparisons, and summaries, and fuzzy-matches plural/singular column names ("categories" →
  `category` column).

## Known limitations / good next steps
1. **Intent parser is rule-based, not LLM-based.** Works well for the common analyst question
   shapes tested here, but will miss more creative phrasing ("which of my products underperformed
   expectations?"). Natural next step: swap `parse_question()` for an LLM call that returns the
   same `Intent` JSON shape — the rest of the pipeline doesn't need to change.
2. **Single-table analysis only** — no joins across multiple uploaded files yet.
3. **Chart types are limited to bar/line.** Easy to extend `visualizer.py` with pie/scatter/heatmap.
4. **No conversational memory** — each `ask()` call is independent; a web UI wrapper would want to
   keep a running chat + let follow-up questions ("now break that down by region") refer back to
   the last result.

## Turning this into a web UI (next phase, per your priority order)
The core is UI-agnostic on purpose — `agent.ask()` returns a plain dataclass (explanation string +
DataFrame + chart path), so it can be dropped behind:
- a simple **Streamlit/Gradio** app (fastest path to a demo UI), or
- a **FastAPI backend** serving a React/HTML frontend with file upload + chat, or
- as a self-contained **HTML artifact** (upload CSV client-side with PapaParse, call the Claude API
  for the intent-parsing/explanation steps, and do the pandas-equivalent aggregation in JS).

Let me know which of these three you want next and I'll build it against this same core.
