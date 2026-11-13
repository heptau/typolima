"""Regression tests for bugs found during the project review (see CHANGELOG)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path to import typolima
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import typolima.core as typolima  # noqa: E402

NBSP = " "


def run_cli(*args, cwd=None):
    """Run the CLI in a subprocess and return the CompletedProcess."""
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "typolima", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
    )


class TestProtectedSpans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs = typolima.load_rules("cs")
        cls.en = typolima.load_rules("en")
        cls.fr = typolima.load_rules("fr")

    def test_urls_and_emails_untouched(self):
        for text in (
            "www.Example.Com",
            "John.Doe@example.com",
            "https://a.cz/x--y/1234567?q=A.B",
        ):
            self.assertEqual(typolima.fix_text(text, self.cs), text)
        # French puts a space before ":" and "?", but not inside a URL.
        self.assertEqual(
            typolima.fix_text("Voir https://example.com/a?b=1", self.fr),
            "Voir https://example.com/a?b=1",
        )

    def test_html_entities_untouched(self):
        text = "AT&amp;T a&nbsp;text &quot;x&quot; &#8211; &#x2013;"
        self.assertEqual(typolima.fix_text(text, self.cs), text)
        self.assertEqual(typolima.fix_text("a&nbsp;b", self.fr), "a&nbsp;b")

    def test_template_tags_untouched(self):
        for text in (
            '{{< figure src="a.png" title="x" >}}',
            '{{ if eq .Lang "cs" }}',
            '{% include "a -- b.html" %}',
            '{if $a > 5}',
            '<?php echo $a > $b ? "x -- y" : "z"; ?>',
        ):
            self.assertEqual(typolima.fix_text(text, self.cs), text)

    def test_text_around_protected_span_is_still_fixed(self):
        self.assertEqual(
            typolima.fix_text('"Ahoj" {{ .Title }} -- "svete"', self.cs),
            f"„Ahoj“ {{{{ .Title }}}}{NBSP}– „svete“",
        )

    def test_french_time_is_not_split(self):
        self.assertEqual(typolima.fix_text("10:30", self.fr), "10:30")
        self.assertEqual(typolima.fix_text("Quoi?", self.fr), f"Quoi{NBSP}?")


class TestTextRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs = typolima.load_rules("cs")
        cls.en = typolima.load_rules("en")

    def test_unit_rule_does_not_join_lines(self):
        self.assertEqual(
            typolima.fix_text("v roce 2020\nByl to rok", self.cs),
            f"v{NBSP}roce 2020\nByl to rok",
        )

    def test_unit_rule_keeps_identifiers_and_ordinals(self):
        self.assertEqual(typolima.fix_text("H2O, B2B, 3D, 4K", self.cs), "H2O, B2B, 3D, 4K")
        self.assertEqual(typolima.fix_text("1st, 2nd, 3rd, 4th", self.en), "1st, 2nd, 3rd, 4th")
        # Real units still get their non-breaking space.
        self.assertEqual(typolima.fix_text("5kg", self.cs), f"5{NBSP}kg")
        self.assertEqual(typolima.fix_text("5 kg", self.cs), f"5{NBSP}kg")

    def test_leading_period_words_untouched(self):
        text = "framework .NET, soubor .gitignore"
        self.assertEqual(typolima.fix_text(text, self.cs), text)
        self.assertEqual(typolima.fix_text("konec .", self.cs), "konec.")

    def test_indentation_and_trailing_spaces_kept(self):
        self.assertEqual(typolima.fix_text("x\n    y  z  \nw", self.en), "x\n    y z  \nw")

    def test_bracket_cleanup_keeps_line_breaks(self):
        self.assertEqual(typolima.fix_text("( x )", self.en), "(x)")
        self.assertEqual(typolima.fix_text("(\n  x\n)", self.en), "(\n  x\n)")

    def test_single_quoted_phrase_is_not_half_converted(self):
        self.assertEqual(typolima.fix_text("'hello' world", self.en), "'hello' world")
        self.assertEqual(typolima.fix_text("the users' data", self.en), f"the{NBSP}users’ data")

    def test_default_dash_fallback_ignores_double_space(self):
        # pt.yaml has no "dashes" section, so the built-in fallback applies.
        pt = typolima.load_rules("pt")
        self.assertNotIn("–", typolima.fix_text("dois  espaços", pt))
        self.assertIn("–", typolima.fix_text("um - dois", pt))

    def test_rules_without_unit_nnbsp(self):
        # Used to raise NameError: the unit pattern was defined only when
        # numbers.unit_nnbsp was enabled, but the price rule always used it.
        rules = {"language": "X", "locale": "x", "numbers": {"unit_nnbsp": False}}
        self.assertEqual(typolima.fix_text("100,- Kč", rules), f"100,{NBSP}–{NBSP}Kč")

    def test_load_rules_returns_independent_copy(self):
        rules = typolima.load_rules("cs")
        rules["_aggressive_active"] = True
        self.assertNotIn("_aggressive_active", typolima.load_rules("cs"))


class TestMarkdown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs = typolima.load_rules("cs")

    def test_inline_code_and_links_untouched(self):
        md = 'Viz `a -- "b"` a [odkaz](https://a.cz/x--y "titulek") <a href="x">.\n'
        self.assertEqual(typolima.fix_markdown(md, self.cs), md.replace(" a ", f" a{NBSP}"))

    def test_tilde_fence_untouched(self):
        md = 'Text\n\n~~~\na -- "b"\n~~~\n'
        self.assertEqual(typolima.fix_markdown(md, self.cs), md)

    def test_frontmatter_with_dashes_in_value(self):
        md = '---\ntitle: a --- b "q"\n---\n"Text"\n'
        self.assertEqual(
            typolima.fix_markdown(md, self.cs), '---\ntitle: a --- b "q"\n---\n„Text“\n'
        )

    def test_toml_frontmatter(self):
        md = '+++\ntitle = "a -- b"\n+++\n"Text"\n'
        self.assertEqual(
            typolima.fix_markdown(md, self.cs), '+++\ntitle = "a -- b"\n+++\n„Text“\n'
        )

    def test_nested_list_indent_kept(self):
        md = "- a\n  - b\n    - c\n"
        self.assertEqual(typolima.fix_markdown(md, self.cs), md)


class TestHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs = typolima.load_rules("cs")

    def test_preserve_format_keeps_php_blocks(self):
        html = '<?php\n$a = $b > 1 ? "x -- y" : "z";\n?>\n<p>"Ahoj"</p>\n<?php if ($x->y > 3) { echo "a  b"; }\n'
        expected = html.replace('<p>"Ahoj"</p>', "<p>„Ahoj“</p>")
        self.assertEqual(typolima.process_html_preserve_format(html, self.cs), expected)

    def test_preserve_format_keeps_cdata_and_indentation(self):
        html = '<ul>\n    <li>"a"</li>\n</ul>\n<![CDATA[ "x" > "y" ]]>'
        self.assertEqual(
            typolima.process_html_preserve_format(html, self.cs),
            html.replace('"a"', "„a“"),
        )

    def test_process_soup_skips_textarea(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html><body><textarea>"a"</textarea><p>"b"</p></body></html>', "lxml")
        typolima.process_soup(soup, self.cs)
        self.assertIn('<textarea>"a"</textarea>', str(soup))
        self.assertIn("<p>„b“</p>", str(soup))


class TestLanguageDetection(unittest.TestCase):
    def test_normalize_lang(self):
        self.assertEqual(typolima.normalize_lang("CS"), "cs")
        self.assertEqual(typolima.normalize_lang("cz"), "cs")
        self.assertEqual(typolima.normalize_lang("cs-CZ"), "cs")
        self.assertEqual(typolima.normalize_lang("en_us"), "en-US")
        self.assertIsNone(typolima.normalize_lang("xx"))
        self.assertIsNone(typolima.normalize_lang(None))

    def test_html_lang_with_region(self):
        self.assertEqual(typolima.detect_lang_from_html('<html lang="cs-CZ">'), "cs")
        self.assertIsNone(typolima.detect_lang_from_html('<html data-lang="cs">'))

    def test_document_language_wins_over_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".typolimarc").write_text("language: cs\n", encoding="utf-8")
            page = Path(tmp) / "page.html"
            self.assertEqual(typolima.auto_detect_language(page, '<html lang="de">'), "de")
            self.assertEqual(typolima.auto_detect_language(page, "<html>"), "cs")


class TestCli(unittest.TestCase):
    def test_php_file_is_not_reserialized(self):
        php = '<?php\n$a = $b > 1 ? "x" : "y";\n?>\n<p>"Ahoj"</p>\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.php"
            path.write_text(php, encoding="utf-8")
            result = run_cli(str(path), "--lang", "cs", "--in-place")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), php.replace('"Ahoj"', "„Ahoj“"))

    def test_html_fragment_is_not_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial.html"
            path.write_text('<div>\n  {{ if .X }}<p>"Ahoj"</p>{{ end }}\n</div>\n', encoding="utf-8")
            run_cli(str(path), "--lang", "cs", "--in-place")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "<div>\n  {{ if .X }}<p>„Ahoj“</p>{{ end }}\n</div>\n",
            )

    def test_stdout_mode_prints_only_the_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / "a.txt"
            changed.write_text('"Ahoj"\n', encoding="utf-8")
            same = Path(tmp) / "b.txt"
            same.write_text("beze zmen\n", encoding="utf-8")
            self.assertEqual(run_cli(str(changed), "--lang", "cs").stdout, "„Ahoj“\n")
            self.assertEqual(run_cli(str(same), "--lang", "cs").stdout, "beze zmen\n")

    def test_lang_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text('"Ahoj"\n', encoding="utf-8")
            self.assertEqual(run_cli(str(path), "--lang", "CZ").stdout, "„Ahoj“\n")

    def test_missing_path_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(str(Path(tmp) / "nope.txt"), "--lang", "cs")
            self.assertEqual(result.returncode, 1)
            self.assertIn("no such file", result.stderr)

    def test_recursive_honours_include_and_directory_exclude(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            (site / "node_modules" / "pkg").mkdir(parents=True)
            (site / "a.tex").write_text('"x"\n', encoding="utf-8")
            (site / "node_modules" / "pkg" / "b.tex").write_text('"x"\n', encoding="utf-8")
            result = run_cli(
                str(site), "-r", "--lang", "cs", "--dry-run",
                "--include", "*.tex", "--exclude", "node_modules/*",
            )
            self.assertIn("a.tex", result.stdout)
            self.assertNotIn("b.tex", result.stdout)

    def test_config_found_from_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "sub"
            sub.mkdir()
            (Path(tmp) / ".typolimarc").write_text("language: cs\n", encoding="utf-8")
            (sub / "a.txt").write_text('"Ahoj"\n', encoding="utf-8")
            result = run_cli("a.txt", cwd=sub)
            self.assertEqual(result.stdout, "„Ahoj“\n", result.stderr)


if __name__ == "__main__":
    unittest.main()
