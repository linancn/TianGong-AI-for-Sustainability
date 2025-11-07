#!/usr/bin/env python3
"""Compose the TianGong research prompt from the study brief and specs.

By default the script emits a Markdown prompt that references the canonical
workflow and workspace guides instead of inlining their full contents. Pass
``--emit-inline`` to generate the single-line prompt alongside the Markdown
output.

Example:
    uv run python scripts/tooling/compose_inline_prompt.py
    uv run python scripts/tooling/compose_inline_prompt.py --emit-inline
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USER_PROMPT = REPO_ROOT / "user_prompts" / "example.md"
DEFAULT_TEMPLATE = REPO_ROOT / "specs" / "prompts" / "default.md"
DEFAULT_WORKSPACES_GUIDE = REPO_ROOT / "WORKSPACES.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "user_prompts"
MARKDOWN_OUTPUT_FILENAME = "_markdown_prompt.md"
INLINE_OUTPUT_FILENAME = "_inline_prompt.txt"
BRIDGE_PHRASE = "By following the staged workflow strictly"
WORKSPACE_BRIDGE_PHRASE = "Adhere to the study workspace procedures documented here"


def strip_front_matter(raw: str) -> str:
    """Remove leading YAML front matter if present."""
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        return raw
    lines = stripped.splitlines()
    front_matter_end = None
    delimiter_count = 0
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            delimiter_count += 1
            if delimiter_count == 2:
                front_matter_end = idx + 1
                break
    if front_matter_end is None:
        return raw
    remainder = "\n".join(lines[front_matter_end:])
    return remainder.lstrip("\n")


def inline_text(raw: str) -> str:
    """Collapse multiline Markdown into a single line with canonical spacing."""
    lines = (line.strip() for line in raw.replace("\r\n", "\n").splitlines())
    return " ".join(line for line in lines if line)


def extract_headings(markdown: str, max_items: int = 8) -> list[str]:
    """Collect key headings to summarise large sections."""
    headings: list[str] = []
    pattern = re.compile(r"^(#{1,6})\s+(.*)$", flags=re.MULTILINE)
    for match in pattern.finditer(markdown):
        level = len(match.group(1))
        if level > 3:
            continue
        title = match.group(2).strip()
        if title:
            headings.append(title)
        if len(headings) >= max_items:
            break
    return headings


def compose_prompt(user_text: str, template_text: str, workspace_text: str) -> tuple[str, str]:
    """Combine the user prompt with summary references to specs and guides."""
    workspace_clean = strip_front_matter(workspace_text).strip()
    template_clean = template_text.strip()
    user_clean = user_text.strip()

    user_inline = inline_text(user_clean)
    template_inline = inline_text(template_clean)
    workspace_inline = inline_text(workspace_clean)

    template_headings = extract_headings(template_clean)
    workspace_headings = extract_headings(workspace_clean)
    template_summary = "; ".join(template_headings) if template_headings else template_inline
    workspace_summary = "; ".join(workspace_headings) if workspace_headings else workspace_inline

    workflow_bullets = "\n".join(f"- {heading}" for heading in template_headings) if template_headings else "- Refer to `specs/prompts/default.md`."
    workspace_bullets = "\n".join(f"- {heading}" for heading in workspace_headings) if workspace_headings else "- Refer to `WORKSPACES.md`."

    inline_prompt = (
        f"[StudyBrief] {user_inline} | "
        f"[WorkflowSpec] Reference specs/prompts/default.md ({template_summary}) | "
        f"[WorkspaceRules] Reference WORKSPACES.md ({workspace_summary})"
    )

    markdown_sections = [
        "# TianGong Research Prompt",
        "## 1. Study Brief",
        user_clean,
        "---",
        "## 2. Workflow Specification (specs/prompts/default.md)",
        f"{BRIDGE_PHRASE}. Reference the canonical workflow at `specs/prompts/default.md`.",
        "### Key Sections",
        workflow_bullets,
        "### Study-Specific Notes",
        "- Document deterministic command queues, required sources, and overrides here.",
        "---",
        "## 3. Workspace Operations (WORKSPACES.md)",
        f"{WORKSPACE_BRIDGE_PHRASE}. Reference `WORKSPACES.md` for canonical workspace rules.",
        "### Key Sections",
        workspace_bullets,
        "### Workspace Notes",
        "- Record cache paths, logging requirements, and outstanding exceptions here.",
    ]
    markdown_prompt = "\n\n".join(section for section in markdown_sections if section.strip())
    return inline_prompt, markdown_prompt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Markdown prompt that combines the study brief with the "
            "TianGong workflow and workspace specifications."
        )
    )
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
        "--markdown-output",
        "--output",
        dest="markdown_output",
        type=Path,
        help=(
            "Path to write the Markdown prompt. Provide a directory to use the "
            f"default filename ({MARKDOWN_OUTPUT_FILENAME}). Defaults to "
            f"{DEFAULT_OUTPUT_DIR / MARKDOWN_OUTPUT_FILENAME}."
        ),
    )
    parser.add_argument(
        "--emit-inline",
        action="store_true",
        help="Emit the single-line prompt alongside the Markdown output.",
    )
    parser.add_argument(
        "--inline-output",
        type=Path,
        help=(
            "Path to write the inline prompt when --emit-inline is enabled. "
            f"Defaults to {DEFAULT_OUTPUT_DIR / INLINE_OUTPUT_FILENAME}."
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

    if args.markdown_output:
        if args.markdown_output.is_dir() or args.markdown_output.suffix == "":
            output_dir = args.markdown_output
            markdown_path = output_dir / MARKDOWN_OUTPUT_FILENAME
        else:
            markdown_path = args.markdown_output
            output_dir = markdown_path.parent
    else:
        output_dir = DEFAULT_OUTPUT_DIR
        markdown_path = output_dir / MARKDOWN_OUTPUT_FILENAME

    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_prompt, encoding="utf-8")

    emit_inline = args.emit_inline or args.inline_output is not None
    inline_path = None
    if emit_inline:
        inline_path = args.inline_output or output_dir / INLINE_OUTPUT_FILENAME
        inline_path.parent.mkdir(parents=True, exist_ok=True)
        inline_path.write_text(inline_prompt, encoding="utf-8")

    if args.markdown_output is None:
        print(f"Saved markdown prompt to {markdown_path}", file=sys.stderr)
        if inline_path:
            print(f"Saved inline prompt to {inline_path}", file=sys.stderr)

    if emit_inline:
        print(inline_prompt)
    else:
        print(markdown_prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
