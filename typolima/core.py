#!/usr/bin/env python3
"""
typolima – conservative typographic fixer for HTML/text
"""

import argparse
import difflib
import re
import sys
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from bs4 import BeautifulSoup, NavigableString
    from bs4.element import PreformattedString
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
    "en": "en", "en-us": "en-US", "en-gb": "en-GB",
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


def normalize_lang(raw: Any) -> Optional[str]:
    """
    Map a user/document supplied language tag to a supported rules name.

    Accepts any case and both separators ("EN_us" -> "en-US") and falls back
    to the primary subtag for regional variants without their own rules
    ("cs-CZ" -> "cs", "de-AT" -> "de"). Returns None for unknown languages.
    """
    if not raw or not isinstance(raw, str):
        return None
    tag = raw.strip().lower().replace("_", "-")
    if tag in LANG_CODE_MAP:
        return LANG_CODE_MAP[tag]
    primary = tag.split("-", 1)[0]
    return LANG_CODE_MAP.get(primary)


def detect_lang_from_html(content: str) -> str:
    """Detect language from <html lang=""> attribute."""
    # \s before "lang" so that data-lang="" / hreflang="" are not picked up.
    match = re.search(r'<html\b[^>]*\slang\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    if match:
        return normalize_lang(match.group(1))
    return None


def detect_lang_from_filename(path: Path) -> str:
    """Detect language from filename pattern like article.cs.html or article.en-US.md"""
    name = path.stem.lower()

    match = re.search(r'\.([a-z]{2}(?:[-_][a-z]{2})?)$', name)
    if match:
        return normalize_lang(match.group(1))

    return None


def _config_search_dirs(path: Path) -> List[Path]:
    """
    Directories to look for .typolimarc in: the given directory (or the
    directory of the given file) and up to four of its parents.

    The path is made absolute first - a relative "page.html" has "." as its
    only parent, so the project root above the current directory would
    otherwise never be reached.
    """
    try:
        path = path.resolve()
    except OSError:
        path = path.absolute()
    return ([path] + list(path.parents))[:5]


def detect_lang_from_config(path: Path) -> str:
    """Detect language from .typolimarc config file in same or parent directory."""
    return normalize_lang(load_config_from_file(path).get("language"))


def auto_detect_language(path: Path, content: str = None) -> str:
    """
    Auto-detect language from multiple sources, most specific first.

    What the document says about itself wins over the project-wide default:
    the .typolimarc language is only a fallback, otherwise a single config
    file would force one language onto every page of a multilingual site.
    """
    # 1. From HTML lang attribute
    if content:
        lang = detect_lang_from_html(content)
        if lang:
            return lang

    # 2. From filename pattern
    lang = detect_lang_from_filename(path)
    if lang:
        return lang

    # 3. From config file (.typolimarc)
    return detect_lang_from_config(path)


def load_config_from_file(path: Path) -> Dict[str, Any]:
    """Load full configuration from .typolimarc file."""
    for sp in _config_search_dirs(path):
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
    if numbers is not None:
        if not isinstance(numbers, dict):
            raise ValueError(f"Rules for '{lang}': 'numbers' must be a dict")
        labels = numbers.get("identifier_labels")
        if labels is not None and not isinstance(labels, list):
            raise ValueError(f"Rules for '{lang}': 'numbers.identifier_labels' must be a list")

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


@lru_cache(maxsize=None)
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
    # Hand out a copy: callers add run-time flags ("_aggressive_active") and
    # those must not leak into the cached rules of later load_rules() calls.
    return dict(rules)


# A period directly followed by an ASCII uppercase letter - the only place
# where fix_text() has to decide whether to insert a space.
_PERIOD_BEFORE_UPPER = re.compile(r"\.([A-Z])")


def _fix_period_spacing(text: str) -> str:
    """
    Add a space after a period that is glued to the next sentence
    ("končí.Nová věta" -> "končí. Nová věta"), but leave dotted
    abbreviations alone.

    Dotted abbreviations are the reason this cannot be a plain regex: the
    parts are short and separated by periods, so "Ph.D." would be torn into
    "Ph. D.", "LL.M." into "LL. M." and "B.S." into "B. S." - all of which
    are wrong (and destructive) spellings of Czech/international academic
    titles. The rule therefore looks at the word in front of the period:

    * a short (<= 3 letters) token that is itself preceded by a period is
      the tail of a dotted abbreviation ("Ph.D." -> "D", "LL.M." -> "M"),
    * a short token followed by "<uppercase><period>" is its head
      ("B.S." -> "B.", "M.A." -> "M.").

    Anything else is treated as a sentence break and gets the space.
    """
    def repl(match: "re.Match") -> str:
        i = match.start()  # index of the period
        j = i
        while j > 0 and text[j - 1].isascii() and text[j - 1].isalpha():
            j -= 1
        token = text[j:i]
        # A period that does not end a word (" .NET", start of the string) is
        # not a sentence end, so there is nothing to separate.
        if i == 0 or text[i - 1].isspace():
            return match.group(0)
        if token and len(token) <= 3:
            # tail of a dotted abbreviation: "…Ph.D.", "…LL.M.", "…J.A."
            if j > 0 and text[j - 1] == ".":
                return match.group(0)
            # head of a dotted abbreviation: "B.S.", "M.A.", "Ph.D."
            if i + 2 < len(text) and text[i + 2] == ".":
                return match.group(0)
        return ". " + match.group(1)

    return _PERIOD_BEFORE_UPPER.sub(repl, text)


_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Private-use character that no typographic rule produces, used to freeze the
# hyphens of ISO dates while the dash rules run.
_ISO_DATE_SENTINEL = "\uE000"


def _protect_iso_dates(text: str) -> str:
    """
    Freeze the hyphens in ISO dates (2026-10-29).

    The range rule turns "-" between digits into an en-dash ("10-20" ->
    "10–20"), which is right for ranges but wrong for ISO dates: those are
    machine-readable stamps (article metadata, sitemaps, API examples) and
    must keep their hyphens. Restoring happens in _restore_iso_dates().
    """
    return _ISO_DATE_RE.sub(
        lambda m: m.group(0).replace("-", _ISO_DATE_SENTINEL), text
    )


def _restore_iso_dates(text: str) -> str:
    return text.replace(_ISO_DATE_SENTINEL, "-")


# Private-use character standing in for a span that must come through
# fix_text() byte-for-byte (see _protect_spans()).
_SPAN_SENTINEL = "\uE001"

_PROTECTED_SPAN_RE = re.compile(
    "|".join([
        _SPAN_SENTINEL,                                   # a literal sentinel in the input
        r"<\?.*?(?:\?>|\Z)",                              # PHP / processing instructions
        r"\{\{.*?\}\}",                                   # Hugo, Handlebars, Liquid, Jinja output
        r"\{%.*?%\}",                                     # Liquid / Jinja tags
        r"\{[^\s{}][^{}\n]*\}",                            # Latte / single-brace macros
        r"&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#\d{1,7}|#[xX][0-9a-fA-F]{1,6});",  # HTML entities
        r"\b(?:https?|ftp)://[^\s<>\"]+(?<![.,;:!?)\]])",   # URLs
        r"\bwww\.[^\s<>\"]+(?<![.,;:!?)\]])",
        r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",                   # e-mail addresses
    ]),
    re.DOTALL,
)


def _protect_spans(text: str, pattern: "re.Pattern" = _PROTECTED_SPAN_RE) -> tuple:
    """
    Replace everything that is code rather than prose - template tags, PHP
    blocks, HTML entities, URLs, e-mail addresses - with a sentinel character.

    The typographic rules are plain regexes and cannot tell `{{ if eq .Lang
    "cs" }}` or "https://example.com/a--b" from a sentence, so these spans
    are taken out before the rules run and put back afterwards by
    _restore_spans(). Returns (text_with_sentinels, list_of_spans).
    """
    spans: List[str] = []

    def _stash(match: "re.Match") -> str:
        spans.append(match.group(0))
        return _SPAN_SENTINEL

    return pattern.sub(_stash, text), spans


def _restore_spans(text: str, spans: List[str]) -> Optional[str]:
    """
    Put protected spans back in order. Returns None when the number of
    sentinels no longer matches (a custom rule ate or duplicated one) - the
    caller then leaves the text untouched rather than risk misplacing code.
    """
    if text.count(_SPAN_SENTINEL) != len(spans):
        return None
    it = iter(spans)
    return re.sub(_SPAN_SENTINEL, lambda _m: next(it), text)


# Units that are glued to a number on purpose: English ordinals (1st, 2nd)
# and labels such as 3D, 5G, 4K, 10k, 2x, 1080p. Only consulted when the
# source has no space between the number and the letters.
_GLUED_NUMBER_SUFFIXES = {"st", "nd", "rd", "th", "D", "G", "K", "k", "x", "X", "p", "i"}


def fix_text(text: str, rules: Dict[str, Any], context: str = "") -> str:
    """
    Apply typographic rules to a plain text string, leaving template tags,
    PHP blocks, HTML entities, URLs and e-mail addresses untouched.

    `context` is the text immediately preceding the string in the document
    (previous text nodes/siblings). It is only used to recognise identifier
    labels that live in a different element ("IČO: <b>44361751</b>").
    """
    if not text.strip():
        return text

    protected, spans = _protect_spans(text)
    fixed = _restore_spans(_apply_rules(protected, rules, context), spans)
    return text if fixed is None else fixed


def _apply_rules(text: str, rules: Dict[str, Any], context: str = "") -> str:
    """The rule pipeline behind fix_text(); expects protected spans removed."""
    text = _protect_iso_dates(text)

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

        def trailing_apostrophe(match):
            # A straight ' that closes a single-quoted phrase ('hello') is a
            # quotation mark, not an apostrophe - leave the pair alone.
            line = text[text.rfind("\n", 0, match.start()) + 1:match.start() + 1]
            if re.search(r"(?<!\w)'(?=\w)[^']*$", line):
                return match.group(0)
            return f"{match.group(1)}{apo}{match.group(2)}"

        text = re.sub(r"(\w)'(\s|$)", trailing_apostrophe, text)

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

        # Numbers that are identifiers, not quantities, must keep their digits
        # together: an IČO ("IČO: 44361751"), a document/act number ("č. 86327")
        # or a fragment of a URL/query ("?G=86327"). The languages declare the
        # labels that introduce an identifier in `numbers.identifier_labels`.
        identifier_labels = [
            str(lab) for lab in (num.get("identifier_labels") or []) if str(lab).strip()
        ]

        def group_unless_identifier(match):
            start, end = match.span()
            before = text[start - 1] if start else ""
            after = text[end] if end < len(text) else ""
            if (before and before in "/?&=_#@") or (after and after in "/?&=_#@"):
                return match.group(0)
            head = context + text[:start]
            for lab in identifier_labels:
                if re.search(rf"(?:^|[^\w]){re.escape(lab)}[.:]?\s*$", head, re.IGNORECASE):
                    return match.group(0)
            return group(match)

        text = re.sub(r"\b\d{5,}\b", group_unless_identifier, text)

    # Inline whitespace only (space/tab/NBSP) - deliberately excludes \n so a
    # paragraph or list-item break never gets glued to the next line.
    _INLINE_WS = rf"[ \t{UNICODE_NBSP}]"

    # Common units or currency symbols that may follow a number
    units = r"(?:%|[a-zA-Z°]{1,4}|[€$£¥₽₪₺₹]|K[čc])"

    # number + unit → number&nbsp;unit
    if unit_nnbsp:
        def bind_unit(match):
            gap, unit = match.group(2), match.group(3)
            if not gap:
                if unit in _GLUED_NUMBER_SUFFIXES:
                    return match.group(0)
                # Letters on both sides of the number: an identifier such
                # as H2O or B2B, not a quantity with a unit.
                k = match.start()
                while k > 0 and (text[k - 1].isdigit() or text[k - 1] in ".,"):
                    k -= 1
                if k > 0 and text[k - 1].isalpha():
                    return match.group(0)
            return f"{match.group(1)}{UNICODE_NBSP}{unit}"

        text = re.sub(rf"(\d)({_INLINE_WS}*)({units})(?!\w)", bind_unit, text)
        # Handle prefix currencies like $ or £ (mostly English/US)
        text = re.sub(rf"([$£¥]){_INLINE_WS}*(\d)", rf"\1{UNICODE_NBSP}\2", text)

    # Price rounding: 100,- -> 100,– (using en-dash)
    text = re.sub(r"(\d),-", rf"\1,{UNICODE_NBSP}–", text)
    # Currency after price dash: , [NBSP] – Kč -> , [NBSP] – [NBSP] Kč
    # We use [\s\u00A0] to match both regular and non-breaking spaces
    text = re.sub(rf",({_INLINE_WS}*)(–|—){_INLINE_WS}*({units})(?!\w)", rf",\1\2{UNICODE_NBSP}\3", text)

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
            pat_before = r"(\S)(" + _INLINE_WS + r"*)(" + "|".join(before_strs) + r")"

            def space_before(match):
                # "10:30" / "16:9" - a colon between digits is not punctuation.
                nxt = text[match.end()] if match.end() < len(text) else ""
                if (match.group(3) == ":" and not match.group(2)
                        and match.group(1).isdigit() and nxt.isdigit()):
                    return match.group(0)
                return f"{match.group(1)}{UNICODE_NBSP}{match.group(3)}"

            text = re.sub(pat_before, space_before, text)

    if after:
        after_strs = [re.escape(str(c)) for c in after if c and isinstance(c, (str, int, float))]
        if after_strs:
            pat_after = r"(" + "|".join(after_strs) + r")" + _INLINE_WS + r"*(\S)"
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
            # Enhance pattern to handle NBSP if it was already inserted by prepositions.
            # Deliberately NOT \s: that also matches newlines, which would let this
            # eat the line break before a Markdown list item ("\n- foo") and merge
            # it into the previous line.
            pat = pat.replace(" ", _INLINE_WS)
            rep = dr.get("replacement")
            if rep is not None:
                rep = rep.replace("[NBSP]", UNICODE_NBSP).replace("[NNBSP]", UNICODE_NNBSP)
                text = re.sub(pat, rep, text)
    else:
        # Default fallback (conservative)
        text = re.sub(rf"{_INLINE_WS}--?{_INLINE_WS}", rf"{UNICODE_NBSP}– ", text)
        text = re.sub(r"\.{3,}", "…", text)

    # ──────────────────────────────────────
    # 6. Punctuation & Space cleanup (General)
    # ──────────────────────────────────────
    # Clean up spaces inside brackets () [] {} - within a line only, so a
    # line break next to a bracket is never swallowed.
    text = re.sub(r"(\(|\[|\{)[ \t]+(?=\S)", r"\1", text)
    text = re.sub(r"(?<=\S)[ \t]+(\)|\]|\})", r"\1", text)

    # Cleanup spaces inside smart quotes ONLY if they are NOT French/optional style
    if q.get("primary"):
        o, c = q["primary"]
        if o not in after and o not in before:
            text = re.sub(rf"{re.escape(o)}[ \t]+(?=\S)", o, text)
        if c not in before and c not in after:
            text = re.sub(rf"(?<=\S)[ \t]+{re.escape(c)}", c, text)

    # Slash cleanup: A / B -> A/B (conservative for short words/numbers)
    text = re.sub(r"(\w) +/ +(\w)", r"\1/\2", text)

    # Degree symbol: 20°C -> 20 °C (common in CS, SK, DE, FR)
    if rules.get("locale") in ["cs", "sk", "de", "fr"]:
        text = re.sub(r"(\d)°([CF])", rf"\1{UNICODE_NBSP}°\2", text)

    # Avoid spaces before comma, period (always safe)
    # A period that starts a word (".NET", ".gitignore") is not punctuation.
    text = re.sub(r" +(,|\.(?!\w))", r"\1", text)

    # Avoid spaces before !?; ONLY if not required by language (like French)
    if not before:
        text = re.sub(r" +([!?;])", r"\1", text)

    # Ensure space after comma and semicolon (always safe)
    text = re.sub(r"([,;])([A-Za-z])", r"\1 \2", text)

    # Ensure space after period only if followed by an uppercase letter
    # to avoid splitting URLs, hostnames, or lowercase abbreviations.
    # Dotted abbreviations (Ph.D., LL.M., B.S.) are left untouched - see
    # _fix_period_spacing().
    text = _fix_period_spacing(text)

    # Multiple spaces to single space - only between words. Leading spaces
    # are indentation (nested Markdown lists, HTML source layout) and two
    # trailing spaces are a Markdown hard line break.
    text = re.sub(r"(?<=\S) {2,}(?=\S)", " ", text)

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

    return _restore_iso_dates(text)


_FRONTMATTER_RE = re.compile(
    r"\A(---|\+\+\+)[ \t]*\r?\n(?:.*?\r?\n)?\1[ \t]*(?:\r?\n|\Z)", re.DOTALL
)

# Markdown constructs that are code or markup, not prose: fenced code blocks
# (``` and ~~~), inline code spans, link/image targets and raw HTML tags.
_MARKDOWN_CODE_RE = re.compile(
    "|".join([
        _SPAN_SENTINEL,
        r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[ \t]*$|\Z)",   # fenced code blocks
        r"```.*?```",                                     # inline triple-backtick spans
        r"`[^`\n]+`",                                     # inline code
        r"(?<=\])\([^()\s]*(?:[ \t]+\"[^\"\n]*\")?\)",    # link target: [text](url "title")
        r"<!--.*?-->",                                    # HTML comments
        r"</?[a-zA-Z][^<>\n]*>",                          # raw HTML tags
    ]),
    re.DOTALL | re.MULTILINE,
)


def _protect_frontmatter(content: str) -> tuple:
    """
    Extract and protect YAML frontmatter (---...---) at the start of a file.
    Returns (body, frontmatter_block) where frontmatter_block is None if not found.
    """
    # The delimiters must stand on lines of their own: a "---" inside a value
    # ("title: a --- b") does not end the block. Hugo's TOML flavour (+++) is
    # recognised as well.
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return content, None
    return content[match.end():], match.group(0)


# A leading "- " list marker, indented or not. fix_text()'s dash rule turns a
# lone hyphen between two spaces into an en-dash (for parenthetical thoughts),
# which is correct for prose but would also fire on a nested list item like
# "  - text" (the indent before the marker counts as the "space before"),
# rewriting the marker itself into "  – text" and breaking the list.
_LIST_MARKER_RE = re.compile(r"^([ \t]*)-(?=[ \t])", re.MULTILINE)
_LIST_MARKER_PLACEHOLDER = "\x00LISTMARKER\x00"


def _protect_list_markers(content: str) -> str:
    """Replace leading '-' list markers with a placeholder immune to dash rules."""
    return _LIST_MARKER_RE.sub(rf"\1{_LIST_MARKER_PLACEHOLDER}", content)


def _restore_list_markers(content: str) -> str:
    """Restore list marker placeholders back to '-'."""
    return content.replace(_LIST_MARKER_PLACEHOLDER, "-")


def fix_markdown(content: str, rules: Dict[str, Any]) -> str:
    """
    Apply typographic rules to Markdown content while protecting:
    - YAML/TOML frontmatter (---...--- / +++...+++)
    - Fenced code blocks (```...``` and ~~~...~~~) and inline `code`
    - Link/image targets and raw HTML tags
    - Leading '-' list markers (incl. nested/indented ones)
    """
    body, frontmatter = _protect_frontmatter(content)
    protected, code_spans = _protect_spans(body, _MARKDOWN_CODE_RE)
    protected = _protect_list_markers(protected)
    protected = fix_text(protected, rules)
    protected = _restore_list_markers(protected)
    restored = _restore_spans(protected, code_spans)
    if restored is not None:
        body = restored
    return (frontmatter or "") + body


SKIP_TAGS = {"script", "style", "code", "pre", "samp", "var", "kbd", "tt", "textarea"}


def _text_before(node, limit: int = 80) -> str:
    """Text of the preceding siblings (same parent), for rules that need context.

    Text nodes are processed one by one, yet some decisions depend on what
    stands just before them - "IČO:" in <strong>IČO:</strong> 44361751 is a
    separate node from the number, and the number must not be regrouped to
    "44 361 751".
    """
    parts: List[str] = []
    length = 0
    for sibling in node.previous_siblings:
        text = sibling.get_text() if hasattr(sibling, "get_text") else str(sibling)
        parts.append(text)
        length += len(text)
        if length >= limit:
            break
    return "".join(reversed(parts))[-limit:]


def process_soup(soup: BeautifulSoup, rules: Dict[str, Any]):
    """
    Recursively process a BeautifulSoup object, skipping code and script tags.
    """
    def recurse(node, context: str = ""):
        # Comments, doctypes, CDATA sections and processing instructions
        # (<?php ... ?>) are not prose.
        if isinstance(node, PreformattedString):
            return
        if isinstance(node, NavigableString):
            if node.parent and node.parent.name in SKIP_TAGS:
                return
            new = fix_text(str(node), rules, context)
            if new != str(node):
                node.replace_with(new)
        else:
            for child in list(node.children):
                recurse(child, _text_before(child))

    recurse(soup)


# Matches one markup token: an HTML comment, a doctype declaration, or a
# single tag. Used to tokenize HTML without a full parser so that
# --preserve-format can leave every byte of markup untouched.
# PHP blocks / processing instructions and CDATA sections come first: they may
# contain ">" ("$a > $b", "->"), and a PHP block may run to the end of the file
# without a closing "?>".
_MARKUP_TOKEN_RE = re.compile(
    r"(<!--.*?-->|<\?.*?(?:\?>|\Z)|<!\[CDATA\[.*?\]\]>|<!DOCTYPE[^>]*>|<[^>]*>)",
    re.DOTALL | re.IGNORECASE,
)
_TAG_NAME_RE = re.compile(r"^<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9:-]*)")


def process_html_preserve_format(content: str, rules: Dict[str, Any]) -> str:
    """
    Apply typographic fixes to HTML text nodes without re-parsing and
    re-serializing the document through BeautifulSoup/lxml.

    str(BeautifulSoup(...)) normalizes the whole document as a side effect
    (sorts/reflows attributes, rewrites void elements as self-closing,
    collapses inter-tag whitespace, ...), which produces a huge diff
    unrelated to typography. This tokenizes the raw string on tag/comment/
    doctype boundaries instead: every markup token is copied through
    byte-for-byte, and fix_text() only ever runs on the text between them
    (skipping text inside SKIP_TAGS, same as process_soup).

    Trade-off: this is a regex tokenizer, not a real HTML parser, so it
    assumes well-formed markup (no unescaped '>' inside attribute values).
    That's an acceptable trade for a mode whose whole purpose is to
    guarantee zero incidental reformatting.
    """
    tokens = _MARKUP_TOKEN_RE.split(content)
    skip_stack = []
    out = []
    # Tail of the last ~80 characters of *text* seen so far, handed to
    # fix_text() as context (identifier labels often sit in a sibling
    # element, e.g. "<strong>IČO:</strong> 44361751").
    text_tail = ""

    for i, token in enumerate(tokens):
        if i % 2 == 1:
            # Markup token (tag/comment/doctype) - always passed through unchanged.
            out.append(token)
            if not token.startswith(("<!", "<?")):
                m = _TAG_NAME_RE.match(token)
                if m:
                    is_closing = bool(m.group(1))
                    name = m.group(2).lower()
                    if name in SKIP_TAGS:
                        if is_closing:
                            if skip_stack and skip_stack[-1] == name:
                                skip_stack.pop()
                        elif not token.rstrip().endswith("/>"):
                            skip_stack.append(name)
        else:
            if skip_stack:
                out.append(token)
            else:
                fixed = fix_text(token, rules, text_tail)
                out.append(fixed)
                text_tail = (text_tail + fixed)[-80:]

    return "".join(out)


_TEMPLATE_SYNTAX_RE = re.compile(r"<\?|\{\{|\{%")
_HTML_ROOT_RE = re.compile(r"<html[\s>]", re.IGNORECASE)


def _can_reserialize(content: str, suffix: str) -> bool:
    """
    Whether an HTML file may safely go through the BeautifulSoup round-trip.

    Parsing and re-serializing is only harmless for a complete, static HTML
    document. A fragment/partial would get wrapped in <html><body>, PHP
    blocks would be turned into comments ("<!--?php ... ?-->") and template
    control flow would be "repaired" as if it were broken markup - so PHP
    and template files are always edited in place by the tokenizer
    (process_html_preserve_format) instead.
    """
    if suffix not in (".html", ".htm"):
        return False
    if _TEMPLATE_SYNTAX_RE.search(content):
        return False
    return bool(_HTML_ROOT_RE.search(content))


def _matches_pattern(path: Path, patterns: list) -> bool:
    """
    Check if path matches any of the glob patterns. A pattern is tried
    against the file name, the whole path and every trailing part of it, so
    "node_modules/*" also excludes "site/node_modules/pkg/readme.md".
    """
    import fnmatch
    parts = path.parts
    candidates = {path.name, str(path), path.as_posix()}
    candidates.update("/".join(parts[i:]) for i in range(len(parts)))
    for pattern in patterns:
        pattern = str(pattern)
        if any(fnmatch.fnmatch(c, pattern) for c in candidates):
            return True
    return False


def main():
    # Filter out PyInstaller isolation flags that leak into sys.argv[1:].
    # PyInstaller --onefile bundles add interpreter flags like -B -S -I -c
    # to argv, which argparse then mistakes for script arguments.
    # Note: -v is intentionally NOT in this set because TypoLima uses -v
    # as a short alias for --verbose.
    _PY_INTERPRETER_FLAGS = {"-B", "-S", "-I", "-c", "-q", "-O", "-OO", "-E", "-s", "-t"}
    sys.argv[1:] = [a for a in sys.argv[1:] if a not in _PY_INTERPRETER_FLAGS]

    parser = argparse.ArgumentParser(description="typolima – conservative typographic fixer")
    # nargs="*" allows us to handle PyInstaller subprocess invocations
    # silently (they typically have no path argument).
    parser.add_argument("path", nargs="*", help="file or directory")

    # Try to find VERSION file or use package metadata
    version = "unknown"
    # When running as PyInstaller bundle, sys._MEIPASS is the temp folder
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    version_file = base_path / "VERSION"

    if version_file.is_file():
        version = version_file.read_text().strip()
    else:
        try:
            version = get_package_version("typolima")
        except Exception:
            pass

    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")
    parser.add_argument("--lang", help="language: cs, sk, pl, en (en-US, en-GB), fr, de, it, es, pt (pt-PT, pt-BR), uk, hu, ro, nl, bg, vi, tr, ru, el, fi, sv, hr, da, no, sl, et, ca, id, tl, sw, eo")
    parser.add_argument("--auto-detect", "-a", action="store_true", help="auto-detect language from HTML lang attribute, filename, or .typolimarc config")
    parser.add_argument("--in-place", "-i", action="store_true", help="modify files in place")
    parser.add_argument("--backup", "-b", action="store_true", help="create .bak backup before modifying (requires --in-place)")
    parser.add_argument("--dry-run", action="store_true", help="do not write changes")
    parser.add_argument("--diff", action="store_true", help="show diff (requires --dry-run)")
    parser.add_argument("--recursive", "-r", action="store_true", help="process directories recursively")
    parser.add_argument("--aggressive", action="store_true", help="convert (c) to ©, +- to ±, etc.")
    parser.add_argument("--preserve-format", action="store_true", help="for HTML: edit text content only, without re-serializing the document through BeautifulSoup (keeps original attribute order, self-closing style, and whitespace byte-for-byte)")
    parser.add_argument("--include", metavar="PATTERN", action="append", default=[], help="include files matching pattern (glob). Can be used multiple times")
    parser.add_argument("--exclude", metavar="PATTERN", action="append", default=[], help="exclude files matching pattern (glob). Can be used multiple times")
    parser.add_argument("--verbose", "-v", action="store_true", help="show detailed statistics about changes")

    args = parser.parse_args()

    # Load config file to fill in defaults
    config = {}
    if args.path:
        config = load_config_from_file(Path(args.path[0]))

    # Override config with CLI arguments (CLI takes precedence)
    if args.lang is None and config.get("language"):
        args.lang = config.get("language")

    # Glob patterns may be given as a single string in the config file.
    for key in ("include", "exclude"):
        if isinstance(config.get(key), str):
            config[key] = [config[key]]

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

    if not args.preserve_format and config.get("preserve_format"):
        args.preserve_format = config.get("preserve_format")

    if not args.auto_detect and config.get("auto_detect"):
        args.auto_detect = config.get("auto_detect")

    if not args.lang and not args.auto_detect:
        # Distinguish between a real user error and a spurious
        # invocation from a PyInstaller subprocess (bootloader
        # re-execution or multiprocessing child). Subprocesses
        # typically have no path argument.
        if not args.path:
            # Likely a subprocess - exit silently so it does not
            # pollute the user's build output.
            sys.exit(0)
        print("Error: either --lang or --auto-detect is required", file=sys.stderr)
        sys.exit(2)

    # If not auto-detect, load rules once
    default_rules = None
    if not args.auto_detect:
        try:
            # Accept "CS", "cz", "en-us", "cs-CZ"; unknown names are passed
            # on unchanged so the error names what the user typed.
            default_rules = load_rules(normalize_lang(args.lang) or str(args.lang))
            if args.aggressive:
                default_rules["_aggressive_active"] = True
        except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)

    default_extensions = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

    def should_include(path: Path) -> bool:
        """Check if file should be included based on include/exclude patterns."""
        name = path.name.lower()

        if args.include:
            if not _matches_pattern(path, args.include):
                return False
        else:
            if not any(name.endswith(e) for e in default_extensions):
                return False

        if args.exclude:
            if _matches_pattern(path, args.exclude):
                return False

        return True

    paths = []
    seen = set()
    missing = 0
    for p in args.path:
        path = Path(p)
        if path.is_dir():
            if not args.recursive:
                print(f"Warning: {path} is a directory, use --recursive to process it", file=sys.stderr)
                continue
            # Walk everything and let should_include() decide, so --include
            # patterns outside the default extensions are honoured too.
            candidates = sorted(f for f in path.rglob("*") if f.is_file())
        elif path.is_file():
            candidates = [path]
        else:
            print(f"Error: {path}: no such file or directory", file=sys.stderr)
            missing += 1
            continue
        for f in candidates:
            if f not in seen and should_include(f):
                seen.add(f)
                paths.append(f)

    # Without --in-place/--dry-run the fixed text itself goes to stdout, so
    # status messages must stay out of it.
    to_stdout = not args.in_place and not args.dry_run
    status = sys.stderr if to_stdout else sys.stdout

    changed = 0
    errors = 0
    html_extensions = [".html", ".htm", ".php", ".hbs", ".liquid", ".latte"]
    stats = {"quotes": 0, "dashes": 0, "nbsp": 0, "apostrophes": 0, "symbols": 0, "spaces": 0}

    # Show a simple progress indicator for larger batches.
    # For small file counts the per-file "Fixed: ..." output is
    # clearer than a flickering bar.
    show_progress = len(paths) > 5 and sys.stdout.isatty()

    if show_progress:
        import time as _time
        _progress_total = len(paths)
        _progress_start = _time.time()

        def _make_progress_iter():
            import sys as _sys
            n = 0
            for p in paths:
                n += 1
                elapsed = _time.time() - _progress_start
                avg = elapsed / n if n else 0
                if avg < 0.001:
                    avg_str = f"{avg * 1_000_000:.0f}us"
                elif avg < 1:
                    avg_str = f"{avg * 1000:.1f}ms"
                else:
                    avg_str = f"{avg:.2f}s"
                # \r to overwrite, spaces to clear leftover chars
                _sys.stderr.write(
                    f"\rProcessing: {n}/{_progress_total} "
                    f"[{elapsed:.2f}s, avg {avg_str}/file]   "
                )
                _sys.stderr.flush()
                yield p
            # Clear the progress line at the end
            _sys.stderr.write("\r" + " " * 80 + "\r")
            _sys.stderr.flush()

        iterator = _make_progress_iter()
    else:
        iterator = paths

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
            # An explicit --lang (or config language) is the fallback.
            if not detected_lang:
                detected_lang = normalize_lang(args.lang)
            if not detected_lang:
                print(f"Warning: could not detect language for {path}, skipping", file=sys.stderr)
                errors += 1
                continue
            try:
                rules = load_rules(detected_lang)
                if args.aggressive:
                    rules["_aggressive_active"] = True
            except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
                print(f"Warning: cannot load rules for detected language '{detected_lang}' for {path}: {e}", file=sys.stderr)
                errors += 1
                continue
        else:
            rules = default_rules

        try:
            if path.suffix.lower() in html_extensions:
                if args.preserve_format or not _can_reserialize(orig, path.suffix.lower()):
                    new = process_html_preserve_format(orig, rules)
                else:
                    soup = BeautifulSoup(orig, "lxml")
                    process_soup(soup, rules)
                    new = str(soup)
            elif path.suffix.lower() == ".md":
                new = fix_markdown(orig, rules)
            else:
                new = fix_text(orig, rules)
        except Exception as e:
            print(f"Warning: failed to process {path}: {e}", file=sys.stderr)
            errors += 1
            continue

        if new == orig:
            # Filter mode still has to emit the (unchanged) text.
            if to_stdout:
                sys.stdout.write(new)
            continue

        changed += 1

        if args.verbose:
            # Straight quotes that disappeared were replaced by typographic
            # ones; en/em dashes and NBSPs that appeared were inserted.
            def _count(text, chars):
                return sum(text.count(c) for c in chars)

            stats["quotes"] += max(0, orig.count('"') - new.count('"'))
            stats["dashes"] += max(0, _count(new, "–—") - _count(orig, "–—"))
            stats["nbsp"] += max(0, _count(new, "\u00a0\u202f") - _count(orig, "\u00a0\u202f"))

        if args.dry_run:
            if args.diff:
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
                sys.stdout.write(new)

    if args.dry_run:
        print(f"\nWould fix {changed} file(s)", file=status)
    else:
        print(f"\nFixed {changed} file(s)", file=status)

    if errors > 0:
        print(f"\n{errors} file(s) skipped due to errors", file=sys.stderr)

    if args.verbose and changed > 0:
        print("\n--- Change Statistics ---", file=status)
        if stats["quotes"]:
            print(f"  Quotes fixed: {stats['quotes']}", file=status)
        if stats["dashes"]:
            print(f"  Dashes converted: {stats['dashes']}", file=status)
        if stats["nbsp"]:
            print(f"  Non-breaking spaces added: {stats['nbsp']}", file=status)

    # A path that does not exist is a user error, not a skipped file.
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
