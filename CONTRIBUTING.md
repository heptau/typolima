# Contributing to TypoLima

Thank you for your interest in improving TypoLima! We welcome contributions, especially new language rules or improvements to existing ones.

## Adding a New Language

Typographic rules are stored as YAML files in `typolima/rules/`. To add a new language:

1.  Identify the ISO 639-1 language code (e.g., `es` for Spanish, `pl` for Polish).
2.  Create a new file `typolima/rules/<code?️.yaml`.
3.  Fill in the rules. You can use `cs.yaml` or `en.yaml` as a template.
4.  Add the new language code to the `--lang` help description in `typolima/core.py`.
5.  Add a test case in `tests/test_typolima.py` to verify the new rules.

## Development Workflow

We use a `Makefile` to simplify development tasks.

### Prerequisites

- Python 3.9+
- `pip install build pyinstaller beautifulsoup4 pyyaml`

### Common Commands

- **Run tests:** `make test`
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

## Versioning

We use a single `VERSION` file in the root of the repository to manage the project version. The `Makefile` and `pyproject.toml` use this file as the single source of truth.
