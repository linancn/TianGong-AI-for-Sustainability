#!/usr/bin/env python3
"""
Compose an inline research prompt by combining the AI infrastructure brief
with the staged workflow instructions from the default template.

Example:
    uv run python scripts/compose_inline_prompt.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER_PROMPT = REPO_ROOT / "user_prompts" / "ai-infra.md"
DEFAULT_TEMPLATE = REPO_ROOT / "specs" / "prompts" / "default.md"
DEFAULT_OUTPUT_FILENAME = "inline_prompt.txt"
BRIDGE_PHRASE = "By following the staged workflow strictly"


def inline_text(raw: str) -> str:
    """Collapse multiline Markdown into a single line with canonical spacing."""
    lines = (line.strip() for line in raw.replace("\r\n", "\n").splitlines())
    return " ".join(line for line in lines if line)


def compose_prompt(user_text: str, template_text: str) -> str:
    """Combine the user prompt with the staged workflow scaffold."""
    user_inline = inline_text(user_text)
    template_inline = inline_text(template_text)
    return f"{user_inline} {BRIDGE_PHRASE}: {template_inline}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Generate an inline prompt that embeds the AI infrastructure brief " "alongside the default TianGong research workflow."))
    parser.add_argument(
        "--user-prompt",
        type=Path,
        default=DEFAULT_USER_PROMPT,
        help="Path to the human-authored AI infrastructure brief.",
    )
    parser.add_argument(
        "--spec",
        "--template",
        dest="spec",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help=("Path to the staged workflow specification. Defaults to " "specs/prompts/default.md. --template is kept as an alias."),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path to write the inline prompt. Defaults to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        user_text = args.user_prompt.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"User prompt not found: {args.user_prompt}", file=sys.stderr)
        return 1
    try:
        template_text = args.spec.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Specification prompt not found: {args.spec}", file=sys.stderr)
        return 1

    composed = compose_prompt(user_text, template_text)

    output_path = args.output or Path.cwd() / DEFAULT_OUTPUT_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(composed, encoding="utf-8")

    if args.output is None:
        print(f"Saved inline prompt to {output_path}", file=sys.stderr)

    print(composed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
