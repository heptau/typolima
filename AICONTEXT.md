# AI Context – TypoLima

## Project Overview
**TypoLima** is a conservative typographic fixer for HTML, PHP, and text files. The name comes from the Latin "lima" (file/polish), representing the final meticulous polishing of a text. It aims to improve text readability while being extremely careful not to break code fragments or technical text.

## Core Principles
1. **Conservative:** If in doubt, do nothing. Do not break HTML tags, scripts, or templates (Hugo, PHP).
2. **Language-Specific:** Rules are defined in YAML files per language code (e.g., `cs.yaml`, `en.yaml`).
3. **Transparent:** Dry-run and diff modes show exactly what would change before any file is modified.

## Tech Stack
- **Python 3.9+**
- **BeautifulSoup4:** For robust HTML parsing and manipulation.
- **PyYAML:** For loading language-specific rules.
- **difflib:** Standard library for generating diffs.

## Project Structure
- `pyproject.toml`: Modern Python package configuration.
- `typolima/`: Core package folder.
  - `core.py`: Main typographic fixing logic.
  - `rules/`: Language-specific YAML rules.
  - `__main__.py`: CLI entry point.
- `tests/`: Unittest-based test suite.
- `AICONTEXT.md`: This context file.
- `CONTRIBUTING.md`: Guidelines for contributors.
- `Makefile`: Build and release automation.
- `VERSION`: Single source of truth for versioning.
- `.goreleaser.yaml`: Release configuration.

## Key Rules & logic
- **Quotes:** Replaces straight quotes with language-specific ones (e.g., „“ for Czech, «» for French).
- **Non-breaking spaces (NBSP):** Inserted after single-letter prepositions and before units.
- **Punctuation:** Adds or fixes spaces around punctuation as required by the language (e.g., French spacing before `!`, `?`, `:`, `;`).
- **Dashes & Ellipsis:** Converts `--` to `–`, `---` to `—`, and `...` to `…`.
- **Aggressive mode:** Optional conversion of symbols like `(c)` to `©`, `+-` to `±`.

## Roadmap / Improvements
- [x] Add robust testing suite (`unittest`).
- [x] Implement basic `--aggressive` mode (symbols, etc.).
- [x] Add more languages (16 languages supported).
- [x] Automate builds and releases (Makefile + GoReleaser).
- [ ] Support for LaTeX or Markdown-specific enhanced typography.
- [ ] Better CLI progress indicators for large projects.
