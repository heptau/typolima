#!/usr/bin/env python3
"""
typofix – conservative typographic fixer for HTML/text
"""

import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    from bs4 import BeautifulSoup, NavigableString, Comment, Doctype
    import yaml
except ImportError:
    print("Error: missing dependencies", file=sys.stderr)
    print("Run: pip install beautifulsoup4 pyyaml", file=sys.stderr)
    sys.exit(1)


UNICODE_NBSP = "\u00A0"
UNICODE_NNBSP = "\u202F"  # narrow NBSP – optional


def load_rules(lang: str, rules_dir: Path = None) -> Dict[str, Any]:
    """
    Load typographic rules from a YAML file.
    """
    if rules_dir is None:
        rules_dir = Path(__file__).parent / "rules"

    path = rules_dir / f"{lang}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Rules file for language '{lang}' not found at {path}")

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def fix_text(text: str, rules: Dict[str, Any]) -> str:
    """
    Apply typographic rules to a plain text string.
    """
    if not text.strip():
        return text

    # ──────────────────────────────────────
    # 1. Quotes – simple version first
    # ──────────────────────────────────────
    q = rules.get("quotes", {})
    if q.get("primary"):
        open_p, close_p = q["primary"]
        # Very conservative – only replace "..." when looks like direct speech
        text = re.sub(r'(?<!\w)"([^"]+)"(?!\w)', rf"{open_p}\1{close_p}", text)

    # secondary / nested – skip for now (can be added later)

    # ──────────────────────────────────────
    # 2. Non-breaking spaces – prepositions
    # ──────────────────────────────────────
    preps = rules.get("non_breaking_prepositions", [])
    if preps and isinstance(preps, list):
        # Filter for strings only to avoid TypeError in re.escape
        preps_strs = [re.escape(str(p)) for p in preps if p and isinstance(p, (str, int, float))]
        if preps_strs:
            pat = r"\b(" + "|".join(preps_strs) + r") +(\S)"
            text = re.sub(pat, rf"\1{UNICODE_NBSP}\2", text, flags=re.IGNORECASE)

    # ──────────────────────────────────────
    # 3. Apostrophes – smart ones
    # ──────────────────────────────────────
    apo = rules.get("apostrophe")
    if apo:
        # Replace straight ' with smart apostrophe (usually ’)
        # Only if between words or at the end of a word (e.g. users')
        text = re.sub(r"(\w)'(\w)", rf"\1{apo}\2", text)
        text = re.sub(r"(\w)'(\s|$)", rf"\1{apo}\2", text)

    # ──────────────────────────────────────
    # 3. Numbers & units
    # ──────────────────────────────────────
    num = rules.get("numbers", {})
    thousands_sep = num.get("thousands_sep", "")
    decimal_sep = num.get("decimal_sep", ".")
    unit_nnbsp = num.get("unit_nnbsp", False)

    if thousands_sep:
        # 1234567 → 1 234 567   (very simple – can be improved)
        def group(match):
            return re.sub(r"(\d)(?=(\d{3})+(?!\d))", rf"\1{thousands_sep}", match.group(0))
        text = re.sub(r"\b\d{5,}\b", group, text)

    # number + unit → number&nbsp;unit
    if unit_nnbsp:
        # Matches numbers followed by optional space and common units or currency symbols
        units = r"(?:%|[a-zA-Z°]{1,4}|[€$£¥₽₪₺₹]|K[čc])"
        text = re.sub(rf"(\d)\s*({units})\b", rf"\1{UNICODE_NBSP}\2", text)
        # Handle prefix currencies like $ or £ (mostly English/US)
        text = re.sub(rf"([$£¥])\s*(\d)", rf"\1{UNICODE_NBSP}\2", text)

    # Price rounding: 100,- -> 100,– (using en-dash)
    text = re.sub(r"(\d),-", rf"\1,{UNICODE_NBSP}–", text)
    # Currency after price dash: , [NBSP] – Kč -> , [NBSP] – [NBSP] Kč
    # We use [\s\u00A0] to match both regular and non-breaking spaces
    text = re.sub(rf",([\s{UNICODE_NBSP}]*)(–|—)[\s{UNICODE_NBSP}]*({units})\b", rf",\1\2{UNICODE_NBSP}\3", text)

    # ──────────────────────────────────────
    # 4. Spaces around punctuation (esp. French)
    # ──────────────────────────────────────
    punc = rules.get("punctuation", {})
    before = [str(c) for c in punc.get("space_before", []) if c]
    after = [str(c) for c in punc.get("space_after", []) if c]

    if before:
        # Filter to ensure we only try to escape strings (to avoid TypeError with bools etc)
        before_strs = [re.escape(str(c)) for c in before if c and isinstance(c, (str, int, float))]
        if before_strs:
            pat_before = r"(\S)\s*(" + "|".join(before_strs) + r")"
            text = re.sub(pat_before, rf"\1{UNICODE_NBSP}\2", text)

    if after:
        after_strs = [re.escape(str(c)) for c in after if c and isinstance(c, (str, int, float))]
        if after_strs:
            pat_after = r"(" + "|".join(after_strs) + r")\s*(\S)"
            text = re.sub(pat_after, rf"\1{UNICODE_NBSP}\2", text)

    # ──────────────────────────────────────
    # 5. Dashes & ellipsis
    # ──────────────────────────────────────
    # Custom dash rules from YAML
    dash_rules = rules.get("dashes", [])
    if dash_rules:
        for dr in dash_rules:
            pat = dr.get("pattern")
            if not pat: continue
            # Enhance pattern to handle NBSP if it was already inserted by prepositions
            pat = pat.replace(" ", rf"[\s{UNICODE_NBSP}]")
            rep = dr.get("replacement")
            if rep is not None:
                rep = rep.replace("[NBSP]", UNICODE_NBSP).replace("[NNBSP]", UNICODE_NNBSP)
                text = re.sub(pat, rep, text)
    else:
        # Default fallback (conservative)
        text = re.sub(rf" [\s{UNICODE_NBSP}]*-?[\s{UNICODE_NBSP}]* ", rf"{UNICODE_NBSP}– ", text)
        text = re.sub(r"\.{3,}", "…", text)

    # ──────────────────────────────────────
    # 6. Punctuation & Space cleanup (General)
    # ──────────────────────────────────────
    # Clean up spaces inside brackets () [] {}
    text = re.sub(r"(\(|\[|\{)\s+", r"\1", text)
    text = re.sub(r"\s+(\)|\]|\})", r"\1", text)

    # Cleanup spaces inside smart quotes ONLY if they are NOT French/optional style
    if q.get("primary"):
        o, c = q["primary"]
        if o not in after and o not in before:
            text = re.sub(rf"{re.escape(o)}\s+", o, text)
        if c not in before and c not in after:
            text = re.sub(rf"\s+{re.escape(c)}", c, text)

    # Slash cleanup: A / B -> A/B (conservative for short words/numbers)
    text = re.sub(r"(\w) +/ +(\w)", r"\1/\2", text)

    # Degree symbol: 20°C -> 20 °C (common in CS, SK, DE, FR)
    if rules.get("locale") in ["cs", "sk", "de", "fr"]:
        text = re.sub(r"(\d)°([C|F])", rf"\1{UNICODE_NBSP}°\2", text)

    # Avoid spaces before comma, period (always safe)
    text = re.sub(r" +([.,])", r"\1", text)

    # Avoid spaces before !?; ONLY if not required by language (like French)
    if not before:
        text = re.sub(r" +([!?;])", r"\1", text)

    # Ensure space after comma and period (but NOT for decimals 1,2 or 1.2)
    # This regex ensures we only add a space if the character after is a letter
    text = re.sub(r"([,.;])([A-Za-z])", r"\1 \2", text)

    # Multiple spaces to single space
    text = re.sub(r" {2,}", " ", text)

    # ──────────────────────────────────────
    # 7. Symbols & Common units (Conservative)
    # ──────────────────────────────────────
    # m2 -> m², m3 -> m³ (matched after digits)
    text = re.sub(r"(?<=\d)(m|cm|mm|km)2\b", r"\1²", text)
    text = re.sub(r"(?<=\d)(m|cm|mm|km)3\b", r"\1³", text)

    # ──────────────────────────────────────
    # 8. Custom Regex rules from YAML
    # ──────────────────────────────────────
    custom_rules = rules.get("custom_regex", [])
    if custom_rules:
        for cr in custom_rules:
            pat = cr.get("pattern")
            rep = cr.get("replacement")
            if pat and rep is not None:
                rep = rep.replace("[NBSP]", UNICODE_NBSP).replace("[NNBSP]", UNICODE_NNBSP)
                text = re.sub(pat, rep, text)

    # ──────────────────────────────────────
    # 9. Aggressive mode – optional symbols
    # ──────────────────────────────────────
    if rules.get("_aggressive_active"):
        text = re.sub(r"\(c\)", "©", text, flags=re.IGNORECASE)
        text = re.sub(r"\(r\)", "®", text, flags=re.IGNORECASE)
        text = re.sub(r"\(tm\)", "™", text, flags=re.IGNORECASE)
        text = re.sub(r"\(p\)", "℗", text, flags=re.IGNORECASE)
        text = re.sub(r" \+- ", " ± ", text)
        text = re.sub(r"->", "→", text)
        text = re.sub(r"<-", "←", text)
        text = re.sub(r"==>", "⟹", text)
        text = re.sub(r"<=>", "⇔", text)

    return text


def process_soup(soup: BeautifulSoup, rules: Dict[str, Any]):
    """
    Recursively process a BeautifulSoup object, skipping code and script tags.
    """
    skip_tags = {"script", "style", "code", "pre", "samp", "var", "kbd", "tt"}

    def recurse(node):
        if isinstance(node, (Comment, Doctype)):
            return
        if isinstance(node, NavigableString):
            if node.parent and node.parent.name in skip_tags:
                return
            new = fix_text(str(node), rules)
            if new != str(node):
                node.replace_with(new)
        else:
            for child in list(node.children):
                recurse(child)

    recurse(soup)


def main():
    parser = argparse.ArgumentParser(description="typolima – conservative typographic fixer")
    parser.add_argument("path", nargs="+", help="file or directory")

    # Try to find VERSION file
    version = "unknown"
    # When running as PyInstaller bundle, sys._MEIPASS is the temp folder
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    version_file = base_path / "VERSION"

    if version_file.is_file():
        version = version_file.read_text().strip()

    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")
    parser.add_argument("--lang", required=True, help="language: cs, sk, pl, en (en-US, en-GB), fr, de, it, es, pt (pt-PT, pt-BR), uk, hu, ro, nl, bg, vi, tr, ru, el, fi, sv, hr, da, no, sl, et, ca, id, tl, sw, eo")
    parser.add_argument("--in-place", "-i", action="store_true", help="modify files in place")
    parser.add_argument("--dry-run", action="store_true", help="do not write changes")
    parser.add_argument("--diff", action="store_true", help="show diff (requires --dry-run)")
    parser.add_argument("--recursive", "-r", action="store_true", help="process directories recursively")
    parser.add_argument("--aggressive", action="store_true", help="convert (c) to ©, +- to ±, etc.")

    args = parser.parse_args()

    try:
        rules = load_rules(args.lang)
        if args.aggressive:
            rules["_aggressive_active"] = True
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    extensions = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]
    paths = []
    for p in args.path:
        path = Path(p)
        if path.is_dir() and args.recursive:
            for ext in extensions:
                paths.extend(path.rglob(f"*{ext}"))
        elif path.is_file():
            paths.append(path)

    changed = 0
    html_extensions = [".html", ".htm", ".php", ".hbs", ".liquid", ".latte"]

    for path in paths:
        orig = path.read_text(encoding="utf-8")

        if path.suffix.lower() in html_extensions:
            # Use BeautifulSoup for HTML-like files to skip tags/code
            soup = BeautifulSoup(orig, "html.parser")
            process_soup(soup, rules)
            # decode() with default formatter="minimal" is usually best,
            # but we want to ensure NBSP and other symbols are NOT entities.
            # BS4 4.10+ handles this well by default with str().
            new = str(soup)
        else:
            # Pure text/markdown – fix directly to avoid HTML escaping
            new = fix_text(orig, rules)

        if new == orig:
            continue

        changed += 1
        if args.dry_run:
            if args.diff:
                # simple text diff
                print(f"--- {path}")
                print(f"+++ {path} (would change)")
                for line in difflib.unified_diff(
                    orig.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=str(path),
                    tofile=f"{path} (fixed)",
                ):
                    sys.stdout.write(line)
            else:
                print(f"Would change: {path}")
        else:
            if args.in_place:
                path.write_text(new, encoding="utf-8")
                print(f"Fixed: {path}")
            else:
                print(new)

    if args.dry_run:
        print(f"\nWould fix {changed} file(s)")
    else:
        print(f"\nFixed {changed} file(s)")


if __name__ == "__main__":
    main()

