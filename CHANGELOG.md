# Changelog

All notable changes to TypoLima are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Documentation site (`docs/index.html`) redesigned: Source Serif 4 / Inter / JetBrains Mono fonts, light and dark theme, before/after demo, quote specimen section, filterable language table, copy buttons, and new feature descriptions (`--preserve-format`, Markdown protection, numbers and prices).

### Fixed
- The "Supported Languages" table on the docs site listed wrong quotes for several languages (English shown as straight `" "`, Polish and Hungarian as `„ “`) and covered only 14 of 34 rule files. It is now generated from `typolima/rules/*.yaml` by `scripts/gen_docs_languages.py`.

## [1.3.2] - 2026-10-29

### Fixed
- The `darwin-amd64` release archive contained an arm64 binary: `make build-bin` ran PyInstaller once with the build host's architecture, and GoReleaser packed that single file into both archives. Intel Macs therefore got an unexecutable binary from Homebrew or a manual download (`bad CPU type in executable`). The standalone binary is now a universal2 Mach-O (x86_64 + arm64), so both archives carry a file that runs natively on either Mac.
- `make build-bin` no longer borrows the dev virtualenv for PyInstaller. It creates `build-venv` from a universal2 CPython (`BUILD_PYTHON`, by default the python.org install at `/usr/local/bin/python3`) and stops with an explanatory error when that interpreter is single-arch, instead of silently producing an arm64-only bundle. PyYAML is installed from source in that venv, because its wheels ship a single architecture only.

## [1.3.1] - 2026-10-29

### Fixed
- Space-insertion rule after a period (`\.([A-Z])` -> `". "`) tore dotted abbreviations apart: `Ph.D.` became `Ph. D.`, `LL.M.` became `LL. M.`, `B.S.` became `B. S.` and `J.A.Komenský` became `J. A. Komenský`. The rule is now a context-aware replacement (`_fix_period_spacing()`) that leaves a period alone when the token in front of it is the head or the tail of a dotted abbreviation. Normal sentence breaks (`končí.Nová věta` -> `končí. Nová věta`) and abbreviations glued to a name (`Ing.Jiří` -> `Ing. Jiří`) still get their space.
- The range rule (`(?<=\d)-(?=\d)`) rewrote the hyphens of ISO dates - `2026-10-29` came out as `2026–10–29`, which silently breaks machine-readable date stamps in article metadata. ISO dates (`YYYY-MM-DD`) are now frozen while the dash rules run and restored afterwards.
- The thousands-separator rule regrouped numbers that are identifiers rather than quantities: an IČO (`IČO: 44361751`) became `44 361 751`, a document number (`č. 86327`) became `86 327`, and a URL/query fragment (`?G=86327`) was regrouped as well. Numbers are now left alone when they follow a label declared in the new per-language `numbers.identifier_labels` list (cs: `IČO`, `IČ`, `DIČ`, `PSČ`, `ID`, `č`, `číslo`, `kód`, `tel`, `fax`, `vs`, `sp. zn`, ...) or when they are part of a URL/query/code token (`/ ? & = _ # @` next to them).
- `fix_text()` accepts an optional `context` argument with the text immediately preceding the processed string. `process_soup()` and `process_html_preserve_format()` fill it in, so an identifier label that lives in a sibling element (`<strong>IČO:</strong> 44361751`) is still recognised - text nodes used to be processed in isolation, which made the label invisible.

### Added
- Tests for period spacing around dotted abbreviations, ISO dates and identifier numbers (`test_period_spacing_keeps_dotted_abbreviations`, `test_iso_dates_keep_hyphens`, `test_identifiers_are_not_thousands_grouped`).
- `numbers.identifier_labels` added to `validate_rules()` (must be a list when present).

### Known issues
- `--preserve-format` (the regex tokenizer) runs the text rules on raw HTML, so an entity can be mistaken for punctuation: `S&amp;P` gets a space after the `;` (`S&amp; P`). The BeautifulSoup path decodes entities first and is not affected - prefer it for HTML with entities.

## [1.3.0] - 2026-07-27

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
