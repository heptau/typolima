# Contributing to TypoLima

Thank you for your interest in improving TypoLima! We welcome contributions, especially new language rules or improvements to existing ones.

## Adding a New Language

Typographic rules are stored as YAML files in `typolima/rules/`. To add a new language:

1.  Identify the ISO 639-1 language code (e.g., `es` for Spanish, `pl` for Polish).
2.  Create a new file `typolima/rules/<code>.yaml`.
3.  Fill in the rules. You can use `cs.yaml` or `en.yaml` as a template.
4.  Add the new language code to the `--lang` help description in `typolima/core.py`.
5.  Add the language to `LANG_CODE_MAP` and `SUPPORTED_LANGS` in `core.py` if needed.
6.  Add a test case in `tests/test_typolima.py` to verify the new rules.

## CLI Options

TypoLima supports these CLI options:
- `--lang` / `-l` - Language code (required unless using `--auto-detect`)
- `--auto-detect` / `-a` - Auto-detect language from HTML lang attribute, filename, or .typolimarc
- `--in-place` / `-i` - Modify files in place
- `--backup` / `-b` - Create .bak backup before modifying
- `--dry-run` - Show what would change without modifying
- `--diff` - Show detailed diff
- `--recursive` / `-r` - Process directories recursively
- `--aggressive` - Convert (c) → ©, +- → ±, etc.
- `--preserve-format` - HTML only: edit text content without re-serializing via BeautifulSoup, keeping attribute order/self-closing style/whitespace byte-for-byte
- `--include PATTERN` - Include files matching glob pattern
- `--exclude PATTERN` - Exclude files matching glob pattern
- `--verbose` / `-v` - Show detailed statistics about changes
- `.typolimarc` - YAML config file in project root for default settings

## Development Workflow

We use a `Makefile` to simplify development tasks.

### Prerequisites

- Python 3.9+
- `pip install build pyinstaller beautifulsoup4 lxml pyyaml tqdm pytest`

### Common Commands

- **Run tests:** `pytest tests/`
- **Run tests with coverage:** `pytest tests/ -v`
- **Build pip package:** `make build-pip`
- **Build standalone binary:** `make build-bin`
- **Clean build artifacts:** `make clean`

## Code Style

- Follow PEP 8 for Python code.
- Use 4 spaces for indentation in Python files.
- **Always use English for comments** in code and YAML rule files.
- Keep the logic conservative – it is better to skip an uncertain case than to break a file.

## Submitting Changes

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/my-new-language`).
3.  Commit your changes.
4.  Push to the branch (`git push origin feature/my-new-language`).
5.  Submit a Pull Request.

## CI/CD

All changes are automatically tested via GitHub Actions. The workflow runs:
- Tests on Python 3.9
- Build verification on Python 3.11
- Basic linting with flake8

Make sure all tests pass before submitting a PR.

## Versioning

We use a single `VERSION` file in the root of the repository to manage the project version. The `Makefile` and `pyproject.toml` use this file as the single source of truth.

## Releasing

Releases are cut with a single command:

```bash
make release VERSION=X.Y.Z
```

Before running it, make sure `CHANGELOG.md` has real content under `## [Unreleased]` — the command refuses to run if that section is empty, or if `X.Y.Z` already has an entry in the changelog (both would otherwise produce an empty or duplicate GitHub Release).

What it does, in order:
1.  `prepare-release`: writes `X.Y.Z` into `VERSION`, renames `## [Unreleased]` in `CHANGELOG.md` to `## [X.Y.Z] - <today>`, adds a fresh empty `## [Unreleased]` above it for the next cycle, extracts that version's notes into `release-notes.md`, and commits + pushes all of it as a single `Release vX.Y.Z` commit.
2.  Creates and pushes the git tag `vX.Y.Z`.
3.  Runs `goreleaser release --clean --release-notes=release-notes.md`, which builds the macOS binaries (PyInstaller, arm64 + amd64), publishes the GitHub Release using `release-notes.md` as the release body, and updates the formula in `heptau/homebrew-tap`.

### Prerequisites

- `goreleaser` installed locally (`brew install goreleaser`).
- `GITHUB_TOKEN` exported in your shell, with permission to push tags/releases to this repo and to `heptau/homebrew-tap`.
- A clean working tree on `main`, up to date with `origin/main`.

To dry-run the GoReleaser part only (build + package, no publishing, no tag) use `make snapshot`.
