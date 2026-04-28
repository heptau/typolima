# TypoLima – Simple typographic fixer for HTML / text files

[![PyPI](https://img.shields.io/pypi/v/typolima?label=PyPI)](https://pypi.org/project/typolima/)
[![Python](https://img.shields.io/pypi/pyversions/typolima)](https://pypi.org/project/typolima/)
[![License](https://img.shields.io/pypi/l/typolima?label=License)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-29%20passed-brightgreen)](https://github.com/heptau/typolima/actions)
[![CI](https://github.com/heptau/typolima/actions/workflows/test.yml/badge.svg)](https://github.com/heptau/typolima/actions)
[![Platform](https://img.shields.io/pypi/implementation/typolima?label=Platform)](https://pypi.org/project/typolima/)

**TypoLima** is a tiny, conservative command-line tool that fixes common typographic issues in HTML, PHP, Hugo templates and plain text files according to language-specific rules.

> **Why the name?** *TypoLima* combines "Typo" with the Latin word **lima** (file/polish), which was used by classical authors to describe the final, meticulous polishing of a literary work (*labor limae*).

It only touches **text content** (never tags, attributes, scripts, style blocks, Hugo `{{ }}` shortcodes etc.) and prefers to do **nothing** rather than risk breaking something.

## Features

- Smart curly quotes („ “ for cs, « » for fr, etc.)
- Non-breaking spaces after single-letter prepositions (cs, de, fr …)
- NBSP before units (5&nbsp;kg, 20&nbsp;%)
- Intelligent dashes (en-dash `–` for ranges `10–20`, or parenthetical thoughts with NBSP)
- Common abbreviations (cs: `s. r. o.`, `tj.`, `tzn.`)
- Automatic units & symbols: `m2` → `m²`, `cm3` → `cm³`
- Smart prices: `100,-` → `100,–`
- Correct thousands / decimal separators per language
- Spaces around punctuation (especially French style: ? ! : ;)
- Aggressive mode: `(c)` → `©`, `+-` → `±`, `->` → `→` etc.
- Very conservative – skips uncertain cases
- Works on HTML, PHP, Hugo templates, Markdown …

## Supported languages (33+ languages)

**European:** cs, sk, pl, en (en-US, en-GB), de, fr, it, es, pt (pt-PT, pt-BR), nl, hu, ro, bg, uk, ru, el, fi, sv, no, da, hr, sl, et, ca

**Other:** tr, vi, id, tl (Tagalog), sw (Swahili), eo (Esperanto)

Run `typolima --lang cs` (use any supported code) to process files.

## Installation

**Option A – via Homebrew (Recommended for macOS)**  
If you use Homebrew, you can install TypoLima directly from the heptau tap:

```bash
brew install heptau/tap/typolima
```

**Option B – via pipx (Isolated installation)**  
This is the cleanest way to install Python CLI tools without affecting your system Python.

```bash
pipx install git+https://github.com/heptau/typolima.git
```

**Option C – via pip**
You can also install it directly from GitHub using pip:

```bash
pip install git+https://github.com/heptau/typolima.git
```

**Option D – From source**
```bash
git clone https://github.com/heptau/typolima.git
cd typolima
pip install .
```

## Usage

```bash
typolima --help

# Basic usage
typolima article.html --lang cs --in-place

# Show what would change (very useful!)
typolima public/**/*.html --lang fr --dry-run --diff

# Process whole Hugo output
typolima public/ --lang cs --recursive --in-place

# More aggressive mode (convert (c) to ©, +- to ± etc.)
typolima text.md --lang en --aggressive

# Include only specific file types
typolima content/ --lang cs --recursive --include "*.html" --include "*.md"

# Exclude certain files (e.g., partials, includes)
typolima public/ --lang de --recursive --exclude "_*"

# Combine include and exclude
typolima site/ --lang fr --recursive --include "*.html" --exclude "*.min.html"

# With backup (creates .bak files)
typolima *.html --lang cs --in-place --backup

# Auto-detect language from HTML lang attribute, filename, or .typolimarc
typolima site/ --recursive --auto-detect
```

## Hugo integration example (package.json)
```json
{
  "scripts": {
    "postbuild": "typolima public/**/*.html --lang cs --in-place"
  }
}
```

## How conservative is it?

- Only replaces obvious straight quotes → curly
- NBSP after prepositions only when very clear context
- Skips anything inside <code>, <pre>, <script>, {{ … }}, <?php … ?>
- `--dry-run --diff` always shows colorful diff first

## Configuration

### Language-specific options
- `--lang cs` – Czech
- `--lang en` – English (default)
- `--lang en-US` / `--lang en-GB` – US/UK English variants
- `--lang pt-BR` / `--lang pt-PT` – Portuguese variants
- See `--help` for full list

### Common use cases
```bash
# Process multiple file types
typolima content/ --lang cs --recursive --dry-run

# Fix specific extensions only
typolima site/*.html site/*.php --lang de --in-place

# Show detailed diff before applying
typolima public/ --lang fr --diff --dry-run

# Include only specific file patterns (glob)
typolima site/ --lang cs --recursive --include "*.html"

# Exclude files matching pattern
typolima public/ --lang de --recursive --exclude "_*"

# Create backup before in-place changes
typolima site/ --lang cs --in-place --backup

# Auto-detect language from HTML lang attribute, filename pattern, or .typolimarc
typolima site/ --recursive --auto-detect
```

### Config File

Create a `.typolimarc` file in your project root for default settings:

```yaml
language: cs
recursive: true
exclude:
  - "_*"
  - "*.min.*"
```

Example file: [`.typolimarc.example`](.typolimarc.example)

## Troubleshooting

**"Error: missing dependencies"**
```bash
pip install beautifulsoup4 lxml pyyaml
```

**"Rules file not found"**
Make sure you're using a valid language code from the supported list.

**File not changing?**
- Use `--dry-run --diff` to see what would be changed
- Check if file has proper UTF-8 encoding
- Ensure text contains patterns matching the language rules

**Performance issues with many files?**
Use `--recursive` flag which enables caching and optimizations.

## More Information

- **Contributing**: Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to add new languages or report issues.
- **License**: This project is licensed under the [MIT License](LICENSE).
