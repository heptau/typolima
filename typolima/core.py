#!/usr/bin/env python3
"""
typolima – conservative typographic fixer for HTML/text
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
    print("Run: pip install beautifulsoup4 lxml pyyaml", file=sys.stderr)
    sys.exit(1)

from functools import lru_cache

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

LANG_CODE_MAP = {
    "cs": "cs", "cz": "cs",
    "sk": "sk",
    "en": "en", "en-us": "en-US", "en-gb": "en-GB", "en-us": "en-US",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "es": "es",
    "pt": "pt", "pt-br": "pt-BR", "pt-pt": "pt-PT",
    "pl": "pl",
    "nl": "nl",
    "hu": "hu",
    "ro": "ro",
    "bg": "bg",
    "uk": "uk",
    "ru": "ru",
    "tr": "tr",
    "vi": "vi",
    "sv": "sv",
    "fi": "fi",
    "no": "no", "nb": "no",
    "da": "da",
    "hr": "hr",
    "sl": "sl",
    "et": "et",
    "ca": "ca",
    "el": "el",
    "id": "id",
    "tl": "tl",
    "sw": "sw",
    "eo": "eo",
}

SUPPORTED_LANGS = set(LANG_CODE_MAP.values())


def detect_lang_from_html(content: str) -> str:
    """Detect language from <html lang=""> attribute."""
    match = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', content, re.IGNORECASE)
    if match:
        lang_raw = match.group(1).lower().strip()
        if lang_raw in LANG_CODE_MAP:
            return LANG_CODE_MAP[lang_raw]
        if lang_raw in SUPPORTED_LANGS:
            return lang_raw
    return None


def detect_lang_from_filename(path: Path) -> str:
    """Detect language from filename pattern like article.cs.html or article.en-US.md"""
    name = path.stem.lower()

    import re
    match = re.search(r'\.([a-z]{2}(?:-[a-z]{2})?)$', name)
    if match:
        lang_raw = match.group(1)
        if lang_raw in LANG_CODE_MAP:
            return LANG_CODE_MAP[lang_raw]
        if lang_raw in SUPPORTED_LANGS:
            return lang_raw

    return None


def detect_lang_from_config(path: Path) -> str:
    """Detect language from .typolimarc config file in same or parent directory."""
    search_paths = [path] + list(path.parents)

    for sp in search_paths[:5]:
        config_file = sp / ".typolimarc"
        if config_file.is_file():
            try:
                with config_file.open(encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                if config and isinstance(config, dict):
                    lang = config.get("language")
                    if lang and isinstance(lang, str):
                        if lang in LANG_CODE_MAP:
                            return LANG_CODE_MAP[lang]
                        if lang in SUPPORTED_LANGS:
                            return lang
            except Exception:
                pass
        if (sp / ".git").exists():
            break
    return None


def auto_detect_language(path: Path, content: str = None) -> str:
    """Auto-detect language from multiple sources."""
    # 1. From config file (.typolimarc)
    lang = detect_lang_from_config(path)
    if lang:
        return lang

    # 2. From HTML lang attribute
    if content:
        lang = detect_lang_from_html(content)
        if lang:
            return lang

    # 3. From filename pattern
    lang = detect_lang_from_filename(path)
    if lang:
        return lang

    return None


def load_config_from_file(path: Path) -> Dict[str, Any]:
    """Load full configuration from .typolimarc file."""
    search_paths = [path] + list(path.parents)

    for sp in search_paths[:5]:
        config_file = sp / ".typolimarc"
        if config_file.is_file():
            try:
                with config_file.open(encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                if config and isinstance(config, dict):
                    return config
            except Exception:
                pass
        if (sp / ".git").exists():
            break
    return {}
    tqdm = None


UNICODE_NBSP = "\u00A0"
UNICODE_NNBSP = "\u202F"  # narrow NBSP – optional


def validate_rules(rules: Dict[str, Any], lang: str) -> None:
    """
    Validate YAML rules schema and raise ValueError on invalid config.
    """
    if not isinstance(rules, dict):
        raise ValueError(f"Rules for '{lang}' must be a dictionary")

    if "language" not in rules:
        raise ValueError(f"Rules for '{lang}' missing required 'language' field")
    if "locale" not in rules:
        raise ValueError(f"Rules for '{lang}' missing required 'locale' field")

    q = rules.get("quotes")
    if q is not None:
        if not isinstance(q, dict):
            raise ValueError(f"Rules for '{lang}': 'quotes' must be a dict")
        primary = q.get("primary")
        if primary is not None:
            if not isinstance(primary, list) or len(primary) != 2:
                raise ValueError(f"Rules for '{lang}': 'quotes.primary' must be [open, close]")

    dashes = rules.get("dashes")
    if dashes is not None:
        if not isinstance(dashes, list):
            raise ValueError(f"Rules for '{lang}': 'dashes' must be a list")
        for i, d in enumerate(dashes):
            if not isinstance(d, dict):
                raise ValueError(f"Rules for '{lang}': dashes[{i}] must be a dict")
            if "pattern" not in d or "replacement" not in d:
                raise ValueError(f"Rules for '{lang}': dashes[{i}] missing 'pattern' or 'replacement'")

    nbp = rules.get("non_breaking_prepositions")
    if nbp is not None and not isinstance(nbp, list):
        raise ValueError(f"Rules for '{lang}': 'non_breaking_prepositions' must be a list")

    numbers = rules.get("numbers")
    if numbers is not None and not isinstance(numbers, dict):
        raise ValueError(f"Rules for '{lang}': 'numbers' must be a dict")

    punc = rules.get("punctuation")
    if punc is not None and not isinstance(punc, dict):
        raise ValueError(f"Rules for '{lang}': 'punctuation' must be a dict")

    custom = rules.get("custom_regex")
    if custom is not None:
        if not isinstance(custom, list):
            raise ValueError(f"Rules for '{lang}': 'custom_regex' must be a list")
        for i, cr in enumerate(custom):
            if not isinstance(cr, dict):
                raise ValueError(f"Rules for '{lang}': custom_regex[{i}] must be a dict")
            if "pattern" not in cr or "replacement" not in cr:
                raise ValueError(f"Rules for '{lang}': custom_regex[{i}] missing 'pattern' or 'replacement'")


@lru_cache(maxsize=1)
def _load_rules_cached(lang: str, rules_dir_str: str) -> Dict[str, Any]:
    """Cached implementation - rules_dir must be hashable (string)."""
    rules_dir = Path(rules_dir_str)
    path = rules_dir / f"{lang}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Rules file for language '{lang}' not found at {path}")

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_rules(lang: str, rules_dir: Path = None) -> Dict[str, Any]:
    """
    Load typographic rules from a YAML file.
    Uses caching to avoid repeated file I/O.
    """
    if rules_dir is None:
        rules_dir = Path(__file__).parent / "rules"

    rules = _load_rules_cached(lang, str(rules_dir.resolve()))
    validate_rules(rules, lang)
    return rules


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
        text = re.sub(rf"(\d)\s*({units})(?!\w)", rf"\1{UNICODE_NBSP}\2", text)
        # Handle prefix currencies like $ or £ (mostly English/US)
        text = re.sub(rf"([$£¥])\s*(\d)", rf"\1{UNICODE_NBSP}\2", text)

    # Price rounding: 100,- -> 100,– (using en-dash)
    text = re.sub(r"(\d),-", rf"\1,{UNICODE_NBSP}–", text)
    # Currency after price dash: , [NBSP] – Kč -> , [NBSP] – [NBSP] Kč
    # We use [\s\u00A0] to match both regular and non-breaking spaces
    text = re.sub(rf",([\s{UNICODE_NBSP}]*)(–|—)[\s{UNICODE_NBSP}]*({units})(?!\w)", rf",\1\2{UNICODE_NBSP}\3", text)

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

    # Ensure space after comma and semicolon (always safe)
    text = re.sub(r"([,;])([A-Za-z])", r"\1 \2", text)

    # Ensure space after period only if followed by an uppercase letter
    # to avoid splitting URLs, hostnames, or lowercase abbreviations.
    text = re.sub(r"\.([A-Z])", r". \1", text)

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
    parser.add_argument("--lang", help="language: cs, sk, pl, en (en-US, en-GB), fr, de, it, es, pt (pt-PT, pt-BR), uk, hu, ro, nl, bg, vi, tr, ru, el, fi, sv, hr, da, no, sl, et, ca, id, tl, sw, eo")
    parser.add_argument("--auto-detect", "-a", action="store_true", help="auto-detect language from HTML lang attribute, filename, or .typolimarc config")
    parser.add_argument("--in-place", "-i", action="store_true", help="modify files in place")
    parser.add_argument("--backup", "-b", action="store_true", help="create .bak backup before modifying (requires --in-place)")
    parser.add_argument("--dry-run", action="store_true", help="do not write changes")
    parser.add_argument("--diff", action="store_true", help="show diff (requires --dry-run)")
    parser.add_argument("--recursive", "-r", action="store_true", help="process directories recursively")
    parser.add_argument("--aggressive", action="store_true", help="convert (c) to ©, +- to ±, etc.")
    parser.add_argument("--include", metavar="PATTERN", action="append", default=[], help="include files matching pattern (glob). Can be used multiple times")
    parser.add_argument("--exclude", metavar="PATTERN", action="append", default=[], help="exclude files matching pattern (glob). Can be used multiple times")

    args = parser.parse_args()

    # Load config file to fill in defaults
    config = {}
    if args.path:
        config = load_config_from_file(Path(args.path[0]))

    # Override config with CLI arguments (CLI takes precedence)
    if args.lang is None and config.get("language"):
        args.lang = config.get("language")

    if not args.recursive and config.get("recursive"):
        args.recursive = config.get("recursive")

    if not args.include and config.get("include"):
        args.include = config.get("include")

    if not args.exclude and config.get("exclude"):
        args.exclude = config.get("exclude")

    if not args.backup and config.get("backup"):
        args.backup = config.get("backup")

    if not args.aggressive and config.get("aggressive"):
        args.aggressive = config.get("aggressive")

    if not args.auto_detect and config.get("auto_detect"):
        args.auto_detect = config.get("auto_detect")

    if not args.lang and not args.auto_detect:
        print("Error: either --lang or --auto-detect is required", file=sys.stderr)
        sys.exit(2)

    # If not auto-detect, load rules once
    default_rules = None
    if not args.auto_detect:
        try:
            default_rules = load_rules(args.lang)
            if args.aggressive:
                default_rules["_aggressive_active"] = True
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)

    default_extensions = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

    def matches_pattern(path: Path, patterns: list) -> bool:
        """Check if path matches any of the glob patterns."""
        import fnmatch
        name = path.name
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True
        return False

    def should_include(path: Path) -> bool:
        """Check if file should be included based on include/exclude patterns."""
        name = path.name.lower()
        ext = path.suffix.lower()

        if args.include:
            if not matches_pattern(path, args.include):
                return False
        else:
            if not any(name.endswith(e) for e in default_extensions):
                return False

        if args.exclude:
            if matches_pattern(path, args.exclude):
                return False

        return True

    paths = []
    for p in args.path:
        path = Path(p)
        if path.is_dir() and args.recursive:
            for ext in default_extensions:
                for f in path.rglob(f"*{ext}"):
                    if should_include(f):
                        paths.append(f)
        elif path.is_file():
            if should_include(path):
                paths.append(path)

    changed = 0
    errors = 0
    html_extensions = [".html", ".htm", ".php", ".hbs", ".liquid", ".latte"]

    iterator = tqdm(paths, desc="Processing", unit="file", disable=not sys.stdout.isatty()) if tqdm and len(paths) > 1 else paths

    for path in iterator:
        try:
            orig = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"Warning: cannot read {path}: {e}", file=sys.stderr)
            errors += 1
            continue

        # Determine which rules to use
        if args.auto_detect:
            detected_lang = auto_detect_language(path, orig if path.suffix.lower() in html_extensions else None)
            if not detected_lang:
                print(f"Warning: could not detect language for {path}, skipping", file=sys.stderr)
                errors += 1
                continue
            try:
                rules = load_rules(detected_lang)
                if args.aggressive:
                    rules["_aggressive_active"] = True
            except FileNotFoundError:
                print(f"Warning: rules not found for detected language '{detected_lang}' for {path}", file=sys.stderr)
                errors += 1
                continue
        else:
            rules = default_rules

        try:
            if path.suffix.lower() in html_extensions:
                soup = BeautifulSoup(orig, "lxml")
                process_soup(soup, rules)
                new = str(soup)
            else:
                new = fix_text(orig, rules)
        except Exception as e:
            print(f"Warning: failed to process {path}: {e}", file=sys.stderr)
            errors += 1
            continue

        if new == orig:
            continue

        changed += 1
        if args.dry_run:
            if args.diff:
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
                try:
                    if args.backup:
                        import shutil
                        shutil.copy2(path, Path(str(path) + ".bak"))
                    path.write_text(new, encoding="utf-8")
                    print(f"Fixed: {path}")
                except OSError as e:
                    print(f"Warning: cannot write {path}: {e}", file=sys.stderr)
                    errors += 1
            else:
                print(new)

    if args.dry_run:
        print(f"\nWould fix {changed} file(s)")
    else:
        print(f"\nFixed {changed} file(s)")

    if errors > 0:
        print(f"\n{errors} file(s) skipped due to errors", file=sys.stderr)


if __name__ == "__main__":
    main()
