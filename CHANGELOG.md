# Changelog

All notable changes to TypoLima are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `--preserve-format` CLI flag (and matching `preserve_format` `.typolimarc` option) for HTML files. Processes text content only via a lightweight tag/comment/doctype tokenizer instead of round-tripping through BeautifulSoup/lxml, so attribute order, void-element self-closing style, and whitespace/indentation stay byte-for-byte identical outside of the actual typographic changes. Without this flag, `str(BeautifulSoup(...))` re-serializes the whole document as a side effect, burying real typographic fixes in a huge unrelated reformatting diff.

### Fixed
- `test_verbose_short_flag_not_filtered` asserted against `sys.argv` after the test's `finally` block had already restored it to the original value, so the assertion checked stale data and could never actually catch a regression in the `-v`/interpreter-flag filtering logic. Now asserts against the injected argv list itself.
- Add `permissions: contents: read` to GitHub Actions workflow to satisfy CodeQL `actions/missing-workflow-permissions` alerts.
- Markdown processing could merge list items (and the paragraph above them) into a single line. The dash rule's NBSP-aware pattern enhancement rewrote a literal space to `[\s ]`, and `\s` also matches newlines, so it could match the line break right before a `- ` list marker and swallow it. Now restricted to an inline-whitespace class (space/tab/NBSP) that never crosses a line break; same fix applied to the French-style punctuation spacing rules, which had the same issue.
- Nested/indented `- ` list markers (e.g. `  - text`) got their dash rewritten to an en-dash by the same dash rule, since the indentation in front of the marker counted as its "space before" - turning a valid nested bullet into invalid Markdown. `fix_markdown()` now protects leading list markers with a placeholder before running typographic rules, the same way it already protects frontmatter and code blocks.

## [1.2.7] - 2026-06-11

### Added
- Protect frontmatter and code blocks in Markdown files from typographic changes.

## [1.2.6] - 2026-06-02

### Changed
- Replace tqdm progress bar with custom microsecond-aware display.

## [1.2.5] - 2026-06-02

### Fixed
- Disable multiprocessing resource tracker in PyInstaller bundle.

## [1.2.4] - 2026-06-02

### Fixed
- Suppress spurious 'missing --lang' error from PyInstaller subprocesses.

## [1.2.3] - 2026-06-02

### Added
- GitHub funding configuration.

### Fixed
- Add hashlib modules to PyInstaller hidden imports.

## [1.2.2] - 2026-06-02

### Fixed
- Don't filter `-v` (TypoLima `--verbose` short alias).
- Add `array` and `multiprocessing` to PyInstaller hidden imports.

## [1.2.1] - 2026-06-02

### Fixed
- Filter PyInstaller isolation flags from `sys.argv`.

## [1.2.0] - 2026-04-28

### Added
- `--verbose` option with change statistics.
- `.typolimarc` config file support with full documentation and examples.
- `--auto-detect` for language detection from HTML `lang` attribute, filename patterns, or config.
- `--backup` option to create `.bak` files before in-place changes.
- `--include`/`--exclude` file filtering with tests and documentation.
- tqdm progress bar for processing many files.
- YAML schema validation and graceful error handling.
- Documentation website with SEO-friendly landing page.
- GitHub Actions workflow for automated testing.
- GitHub Actions CI badge to README.

### Fixed
- Use `importlib.metadata` for version from installed package.
- Use SPDX license expression instead of deprecated classifier.
- Correct entry point and add `MANIFEST.in` for package data.
- Use GitHub badges instead of missing PyPI data.
- Correct shields.io badge URLs in README.

### Changed
- Use lxml parser and cache rules loading for better performance.

## [1.1.2] - 2026-03-21

### Fixed
- Ensure non-breaking space before non-word symbols (%, °, $).

## [1.1.1] - 2026-03-19

### Fixed
- Prevent URL and hostname splitting by dots.

## [1.1.0] - 2026-03-06

### Added
- Global typographic engine overhaul.

### Fixed
- Call PyInstaller via python module to avoid broken shebang after rename.
- Make build-bin more robust using direct venv paths.

## [1.0.0] - 2026-03-05

### Added
- Initial release of TypoLima v1.0.0.
