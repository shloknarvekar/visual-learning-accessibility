"""Prompt text, one module per pipeline step (for example `analysis.py`, `visual_planning.py`).

Keep prompts as reviewed constants separate from the code that sends them, so prompt changes show up
as small, focused diffs.
"""
