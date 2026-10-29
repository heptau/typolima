#!/usr/bin/env python3
"""Regenerate the "Supported Languages" table in docs/index.html from the YAML rules.

Usage: python scripts/gen_docs_languages.py

The table lives between the LANGS:START / LANGS:END markers, so the docs can
never drift from typolima/rules/*.yaml.
"""
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "typolima" / "rules"
INDEX = ROOT / "docs" / "index.html"
NBSP = " "

START = "<!-- LANGS:START -->"
END = "<!-- LANGS:END -->"


def number_example(numbers):
    """Render 1234.5 the way the language writes it."""
    thousands = numbers.get("thousands_sep", "")
    decimal = numbers.get("decimal_sep", ".")
    if thousands == NBSP:
        thousands = "&nbsp;"
    return f"1{thousands}234{decimal}5"


def features(code, rules):
    """Short list of notable per-language behaviour."""
    out = []
    preps = rules.get("non_breaking_prepositions") or []
    if preps:
        out.append("NBSP after short words")
    if (rules.get("punctuation") or {}).get("space_before"):
        out.append("space before ? ! : ; %")
    if rules.get("custom_regex"):
        out.append("abbreviations")
    return ", ".join(out) or "–"


def build_rows():
    rows = []
    for path in sorted(RULES.glob("*.yaml")):
        code = path.stem
        rules = yaml.safe_load(path.read_text(encoding="utf-8"))
        q = rules["quotes"]
        p_open, p_close = q["primary"]
        s_open, s_close = q.get("secondary", ["", ""])
        quotes = f"{p_open}text{p_close} {s_open}text{s_close}"
        rows.append(
            f'<tr data-q="{html.escape((code + " " + rules["language"]).lower())}">'
            f'<td><code>{code}</code></td>'
            f'<td>{html.escape(rules["language"])}</td>'
            f'<td class="quote-cell" lang="{code}">{html.escape(quotes)}</td>'
            f'<td class="num-cell">{number_example(rules.get("numbers", {}))}</td>'
            f'<td>{html.escape(features(code, rules))}</td>'
            "</tr>"
        )
    return rows


def main():
    text = INDEX.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"Markers {START} / {END} not found in {INDEX}")
    rows = build_rows()
    block = START + "\n" + "\n".join(" " * 24 + r for r in rows) + "\n" + " " * 24 + END
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    INDEX.write_text(text, encoding="utf-8")
    print(f"Wrote {len(rows)} language rows to {INDEX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
