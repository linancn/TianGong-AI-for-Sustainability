#!/usr/bin/env python3
"""
Compose an inline research prompt by combining the AI infrastructure brief
with the staged workflow instructions from the default template.

Example:
    uv run python scripts/tooling/compose_inline_prompt.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USER_PROMPT = REPO_ROOT / "user_prompts" / "example.md"
DEFAULT_TEMPLATE = REPO_ROOT / "specs" / "prompts" / "default.md"
DEFAULT_WORKSPACES_GUIDE = REPO_ROOT / "WORKSPACES.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "user_prompts"
INLINE_OUTPUT_FILENAME = "_inline_prompt.txt"
MARKDOWN_OUTPUT_FILENAME = "_markdown_prompt.md"
BRIDGE_PHRASE = "By following the staged workflow strictly"
WORKSPACE_BRIDGE_PHRASE = "Adhere to the study workspace procedures documented here"


def inline_text(raw: str) -> str:
    """Collapse multiline Markdown into a single line with canonical spacing."""
    lines = (line.strip() for line in raw.replace("\r\n", "\n").splitlines())
    return " ".join(line for line in lines if line)


def compose_prompt(user_text: str, template_text: str, workspace_text: str) -> tuple[str, str]:
    """Combine the user prompt with the workflow scaffold and workspace rules."""
    user_inline = inline_text(user_text)
    template_inline = inline_text(template_text)
    workspace_inline = inline_text(workspace_text)
    inline_prompt = f"{user_inline} {BRIDGE_PHRASE}: {template_inline} {WORKSPACE_BRIDGE_PHRASE}: {workspace_inline}"

    markdown_prompt = "\n\n".join(
        (
            user_text.strip(),
            f"{BRIDGE_PHRASE}:\n{template_text.strip()}",
            f"{WORKSPACE_BRIDGE_PHRASE}:\n{workspace_text.strip()}",
        )
    )
    return inline_prompt, markdown_prompt


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
        help=(
            "Optional path to write the inline prompt. "
            "If a directory is provided, both outputs are stored there; "
            "if a file is provided, it is used for the inline prompt and the markdown "
            "prompt is placed alongside it."
        ),
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

    try:
        workspace_text = DEFAULT_WORKSPACES_GUIDE.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Workspace guide not found: {DEFAULT_WORKSPACES_GUIDE}", file=sys.stderr)
        return 1

    inline_prompt, markdown_prompt = compose_prompt(user_text, template_text, workspace_text)

    if args.output:
        if args.output.is_dir() or args.output.suffix == "":
            output_dir = args.output
            inline_path = output_dir / INLINE_OUTPUT_FILENAME
        else:
            inline_path = args.output
            output_dir = inline_path.parent
        markdown_path = output_dir / MARKDOWN_OUTPUT_FILENAME
    else:
        output_dir = DEFAULT_OUTPUT_DIR
        inline_path = output_dir / INLINE_OUTPUT_FILENAME
        markdown_path = output_dir / MARKDOWN_OUTPUT_FILENAME

    output_dir.mkdir(parents=True, exist_ok=True)
    inline_path.write_text(inline_prompt, encoding="utf-8")
    markdown_path.write_text(markdown_prompt, encoding="utf-8")

    if args.output is None:
        print(f"Saved inline prompt to {inline_path}", file=sys.stderr)
        print(f"Saved markdown prompt to {markdown_path}", file=sys.stderr)

    print(inline_prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
