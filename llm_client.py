"""Optional: wires explainer.call_llm() to a real Claude API call for
richer natural-language narration of results. Not required for the
pipeline to work (explainer.py falls back to templates without it).

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-...

Then in explainer.py, replace the call_llm() body with:
    from llm_client import ask_claude
    return ask_claude(prompt)
"""
import os


def ask_claude(prompt: str, model: str = "claude-sonnet-4-6") -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")
    except Exception as e:
        print(f"[llm_client] LLM call failed, falling back to template: {e}")
        return None
