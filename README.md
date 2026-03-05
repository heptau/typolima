# TypoLima – Simple typographic fixer for HTML / text files

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

## Supported languages (2026)

| Code | Language     | Quotes       | Thousands sep | Decimal sep | NBSP before units? | Special                     |
|------|--------------|--------------|---------------|-------------|--------------------|-----------------------------|
| cs   | Čeština      | „ “          | &nbsp;        | ,           | yes                | v s z k o u a i             |
| en   | English      | “ ”          | ,             | .           | yes                |                             |
| fr   | Français     | « »          | &nbsp;        | ,           | yes                | space before ? ! : ; »      |
| de   | Deutsch      | „ “          | .             | ,           | yes                |                             |
| it   | Italiano     | « » / “ ”    | .             | ,           | yes                |                             |
| es   | Español      | « »          | .             | ,           | yes                |                             |
| pt   | Português    | « » / “ ”    | .             | ,           | yes                |                             |

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

## More Information

- **Contributing**: Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to add new languages or report issues.
- **License**: This project is licensed under the [MIT License](LICENSE).
