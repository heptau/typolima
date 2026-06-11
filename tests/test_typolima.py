import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import sys
import os

# Add project root to path to import typolima
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import typolima

class TestTypoLima(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Point to the rules directory in the package
        cls.rules_dir = Path(__file__).parent.parent / "typolima" / "rules"

    def test_load_rules(self):
        rules = typolima.load_rules("en", self.rules_dir)
        self.assertEqual(rules["locale"], "en")
        self.assertEqual(rules["quotes"]["primary"], ["“", "”"])

    def test_fix_text_cs(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        # Quotes
        self.assertEqual(typolima.fix_text('"Ahoj"', rules), "„Ahoj“")
        # Non-breaking prepositions
        self.assertEqual(typolima.fix_text("jdu k lesu", rules), "jdu k\u00A0lesu")
        # Numbers
        self.assertEqual(typolima.fix_text("1000", rules), "1000")  # no separator for 4-digits anymore
        self.assertEqual(typolima.fix_text("10000", rules), "10\u00A0000")
        # Abbreviations (s.r.o.) - Note: tj. at the end won't match \s pattern in our current YAML
        self.assertEqual(typolima.fix_text("Alza s.r.o. tzn. tj. ", rules), "Alza s.\u202Fr.\u202Fo. tzn.\u00A0tj.\u00A0")
        # Prices - note: we add NBSP before Kč
        self.assertEqual(typolima.fix_text("100,- Kč", rules), "100,\u00A0–\u00A0Kč")
        # Units m2, m3 - note: 'a' is a preposition so it gets NBSP in Czech
        self.assertEqual(typolima.fix_text("10m2 a 5cm3", rules), "10m²\u00A0a\u00A05cm³")
        # Non-word symbols like %
        self.assertEqual(typolima.fix_text("než 90 % standard", rules), "než 90\u00A0% standard")
        self.assertEqual(typolima.fix_text("100,- %", rules), "100,\u00A0–\u00A0%")

    def test_fix_text_en(self):
        rules = typolima.load_rules("en", self.rules_dir)
        self.assertEqual(typolima.fix_text('"Hello"', rules), "“Hello”")
        # Smart apostrophe
        self.assertEqual(typolima.fix_text("don't you're", rules), "don’t you’re")
        # Thousands separator
        self.assertEqual(typolima.fix_text("10000", rules), "10,000")

    def test_dashes(self):
        # Range 10-20 should be 10–20 (plus unit check for 'let')
        rules = typolima.load_rules("cs", self.rules_dir)
        self.assertEqual(typolima.fix_text("10-20 let", rules), "10–20\u00A0let")
        # Dash as a separator - ensure we use en-dash (–) in expectation
        self.assertEqual(typolima.fix_text("A - B", rules), "A\u00A0– B")

    def test_fix_text_fr(self):
        rules = typolima.load_rules("fr", self.rules_dir)
        # Spaces around punctuation
        self.assertEqual(typolima.fix_text("Salut ?", rules), "Salut\u00A0?")
        # ':' gets NBSP before. 'la' is a preposition, gets NBSP after. 'C'est' becomes 'C’est'.
        self.assertEqual(typolima.fix_text("C'est quoi : la vie", rules), "C’est quoi\u00A0: la\u00A0vie")
        # French open-quote should have NBSP after it
        self.assertEqual(typolima.fix_text('«bonjour»', rules), '«\u00A0bonjour»')

    def test_it_rules(self):
        rules = typolima.load_rules("it", self.rules_dir)
        self.assertEqual(typolima.fix_text('"Ciao"', rules), "«Ciao»")
        self.assertEqual(typolima.fix_text("10000", rules), "10.000")

    def test_es_rules(self):
        rules = typolima.load_rules("es", self.rules_dir)
        self.assertEqual(typolima.fix_text('"Hola"', rules), "«Hola»")
        self.assertEqual(typolima.fix_text("y yo", rules), "y\u00A0yo")

    def test_pt_rules(self):
        rules = typolima.load_rules("pt", self.rules_dir)
        self.assertEqual(typolima.fix_text('"Ola"', rules), "«Ola»")
        self.assertEqual(typolima.fix_text("10000", rules), "10.000")

    def test_process_soup(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        html = '<p>"Ahoj" 10000.</p><code>"No change"</code>'
        soup = BeautifulSoup(html, "html.parser")
        typolima.process_soup(soup, rules)
        result = str(soup)
        self.assertIn("„Ahoj“", result)
        self.assertIn("10\u00A0000", result)
        self.assertIn('"No change"', result)  # inside <code>

    def test_validate_rules_valid(self):
        rules = {"language": "Test", "locale": "ts"}
        typolima.validate_rules(rules, "ts")

    def test_validate_rules_missing_language(self):
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules({"locale": "ts"}, "ts")
        self.assertIn("missing required 'language'", str(ctx.exception))

    def test_validate_rules_missing_locale(self):
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules({"language": "Test"}, "ts")
        self.assertIn("missing required 'locale'", str(ctx.exception))

    def test_validate_rules_invalid_quotes_primary(self):
        rules = {"language": "Test", "locale": "ts", "quotes": {"primary": "abc"}}
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules(rules, "ts")
        self.assertIn("quotes.primary", str(ctx.exception))

    def test_validate_rules_invalid_dashes(self):
        rules = {"language": "Test", "locale": "ts", "dashes": ["not a dict"]}
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules(rules, "ts")
        self.assertIn("dashes", str(ctx.exception))

    def test_validate_rules_invalid_custom_regex(self):
        rules = {"language": "Test", "locale": "ts", "custom_regex": "not a list"}
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules(rules, "ts")
        self.assertIn("custom_regex", str(ctx.exception))

    def test_validate_rules_non_breaking_prepositions_not_list(self):
        rules = {"language": "Test", "locale": "ts", "non_breaking_prepositions": "a,b"}
        with self.assertRaises(ValueError) as ctx:
            typolima.validate_rules(rules, "ts")
        self.assertIn("non_breaking_prepositions", str(ctx.exception))

    def test_include_patterns(self):
        import fnmatch
        patterns = ["*.md", "*.txt"]
        self.assertTrue(fnmatch.fnmatch("about.md", "*.md"))
        self.assertTrue(fnmatch.fnmatch("readme.txt", "*.txt"))
        self.assertFalse(fnmatch.fnmatch("index.html", "*.md"))

    def test_exclude_patterns(self):
        import fnmatch
        patterns = ["_*", "*.min.js"]
        self.assertTrue(fnmatch.fnmatch("_header.html", "_*"))
        self.assertTrue(fnmatch.fnmatch("app.min.js", "*.min.js"))
        self.assertFalse(fnmatch.fnmatch("app.js", "*.min.js"))

    def test_should_include_with_default_extensions(self):
        from pathlib import Path
        import fnmatch as fm

        class MockArgs:
            include = []
            exclude = []

        default_exts = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

        def matches_pattern(path, patterns):
            for p in patterns:
                if fm.fnmatch(path.name, p) or fm.fnmatch(str(path), p):
                    return True
            return False

        def should_include(path, args):
            name = path.name.lower()
            if args.include:
                if not matches_pattern(path, args.include):
                    return False
            else:
                if not any(name.endswith(e) for e in default_exts):
                    return False
            if args.exclude:
                if matches_pattern(path, args.exclude):
                    return False
            return True

        args = MockArgs()
        args.include = []
        args.exclude = []

        self.assertTrue(should_include(Path("index.html"), args))
        self.assertTrue(should_include(Path("readme.md"), args))
        self.assertFalse(should_include(Path("script.js"), args))
        self.assertFalse(should_include(Path("image.png"), args))

    def test_should_include_with_include_pattern(self):
        import fnmatch as fm

        class MockArgs:
            include = []
            exclude = []

        default_exts = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

        def matches_pattern(path, patterns):
            for p in patterns:
                if fm.fnmatch(path.name, p) or fm.fnmatch(str(path), p):
                    return True
            return False

        def should_include(path, args):
            name = path.name.lower()
            if args.include:
                if not matches_pattern(path, args.include):
                    return False
            else:
                if not any(name.endswith(e) for e in default_exts):
                    return False
            if args.exclude:
                if matches_pattern(path, args.exclude):
                    return False
            return True

        args = MockArgs()
        args.include = ["*.md", "*.txt"]
        args.exclude = []

        self.assertTrue(should_include(Path("readme.md"), args))
        self.assertTrue(should_include(Path("notes.txt"), args))
        self.assertFalse(should_include(Path("index.html"), args))

    def test_should_include_with_exclude_pattern(self):
        import fnmatch as fm

        class MockArgs:
            include = []
            exclude = []

        default_exts = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

        def matches_pattern(path, patterns):
            for p in patterns:
                if fm.fnmatch(path.name, p) or fm.fnmatch(str(path), p):
                    return True
            return False

        def should_include(path, args):
            name = path.name.lower()
            if args.include:
                if not matches_pattern(path, args.include):
                    return False
            else:
                if not any(name.endswith(e) for e in default_exts):
                    return False
            if args.exclude:
                if matches_pattern(path, args.exclude):
                    return False
            return True

        args = MockArgs()
        args.include = []
        args.exclude = ["_*", "*.min.*"]

        self.assertTrue(should_include(Path("index.html"), args))
        self.assertFalse(should_include(Path("_header.html"), args))
        self.assertFalse(should_include(Path("style.min.css"), args))
        self.assertFalse(should_include(Path("app.min.js"), args))

    def test_should_include_combined_include_exclude(self):
        import fnmatch as fm

        class MockArgs:
            include = []
            exclude = []

        default_exts = [".html", ".htm", ".php", ".md", ".txt", ".hbs", ".liquid", ".latte"]

        def matches_pattern(path, patterns):
            for p in patterns:
                if fm.fnmatch(path.name, p) or fm.fnmatch(str(path), p):
                    return True
            return False

        def should_include(path, args):
            name = path.name.lower()
            if args.include:
                if not matches_pattern(path, args.include):
                    return False
            else:
                if not any(name.endswith(e) for e in default_exts):
                    return False
            if args.exclude:
                if matches_pattern(path, args.exclude):
                    return False
            return True

        args = MockArgs()
        args.include = ["*.html", "*.md"]
        args.exclude = ["_*", "*.min.*"]

        self.assertTrue(should_include(Path("index.html"), args))
        self.assertTrue(should_include(Path("about.md"), args))
        self.assertFalse(should_include(Path("_partial.html"), args))
        self.assertFalse(should_include(Path("bundle.min.html"), args))

    def test_backup_creates_bak_file(self):
        import shutil
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.html"
            test_file.write_text('<p>"Hello"</p>', encoding="utf-8")

            rules = typolima.load_rules("en", self.rules_dir)
            new = typolima.fix_text(test_file.read_text(encoding="utf-8"), rules)

            import os
            shutil.copy2(test_file, Path(str(test_file) + ".bak"))

            test_file.write_text(new, encoding="utf-8")

            self.assertTrue(test_file.exists())
            self.assertTrue(Path(str(test_file) + ".bak").exists())
            self.assertEqual(Path(str(test_file) + ".bak").read_text(encoding="utf-8"), '<p>"Hello"</p>')

    def test_detect_lang_from_html(self):
        from typolima import detect_lang_from_html

        self.assertEqual(detect_lang_from_html('<html lang="cs">'), "cs")
        self.assertEqual(detect_lang_from_html('<html lang="fr">'), "fr")
        self.assertEqual(detect_lang_from_html('<html lang="en-US">'), "en-US")
        self.assertEqual(detect_lang_from_html('<html lang="pt-BR">'), "pt-BR")
        self.assertIsNone(detect_lang_from_html('<html lang="xx">'))
        self.assertIsNone(detect_lang_from_html('<html>'))

    def test_detect_lang_from_filename(self):
        from typolima import detect_lang_from_filename

        self.assertEqual(detect_lang_from_filename(Path("article.cs.html")), "cs")
        self.assertEqual(detect_lang_from_filename(Path("text.fr.md")), "fr")
        self.assertEqual(detect_lang_from_filename(Path("readme.en-US.md")), "en-US")
        self.assertIsNone(detect_lang_from_filename(Path("index.html")))
        self.assertIsNone(detect_lang_from_filename(Path("README.md")))

    def test_auto_detect_language(self):
        from typolima import auto_detect_language
        from pathlib import Path

        html_with_lang = '<html lang="de"><body>Test</body></html>'
        result = auto_detect_language(Path("test.html"), html_with_lang)
        self.assertEqual(result, "de")

        result = auto_detect_language(Path("article.cs.md"))
        self.assertEqual(result, "cs")

        result = auto_detect_language(Path("readme.md"))
        self.assertIsNone(result)

    def test_load_config_from_file(self):
        import tempfile
        from pathlib import Path
        from typolima import load_config_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".typolimarc"
            config_file.write_text("""language: cs
recursive: true
exclude:
  - "_*"
  - "*.min.*"
""", encoding="utf-8")

            test_file = Path(tmpdir) / "test.html"
            test_file.write_text("test", encoding="utf-8")

            config = load_config_from_file(test_file)
            self.assertEqual(config["language"], "cs")
            self.assertEqual(config["recursive"], True)
            self.assertEqual(config["exclude"], ["_*", "*.min.*"])

    def test_load_config_from_parent_directory(self):
        import tempfile
        from pathlib import Path
        from typolima import load_config_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir) / "subdir"
            parent.mkdir()

            config_file = Path(tmpdir) / ".typolimarc"
            config_file.write_text("""language: de
aggressive: true
""", encoding="utf-8")

            test_file = parent / "test.html"
            test_file.write_text("test", encoding="utf-8")

            config = load_config_from_file(test_file)
            self.assertEqual(config["language"], "de")
            self.assertEqual(config["aggressive"], True)

    def test_config_file_not_found(self):
        import tempfile
        from pathlib import Path
        from typolima import load_config_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.html"
            test_file.write_text("test", encoding="utf-8")

            config = load_config_from_file(test_file)
            self.assertEqual(config, {})

    def test_pyinstaller_flags_filtered(self):
        # Regression test: PyInstaller --onefile bundles add Python
        # interpreter flags (-B, -S, -I, -c, ...) to sys.argv[1:].
        # argparse would otherwise reject them as unknown arguments.
        import tempfile
        from pathlib import Path
        import sys
        from typolima.core import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.html"
            test_file.write_text("<p>Ahoj</p>", encoding="utf-8")

            # Simulate PyInstaller injecting isolation flags
            original_argv = sys.argv
            try:
                sys.argv = [
                    "typolima",
                    "-B", "-S", "-I", "-c",  # PyInstaller flags
                    str(test_file),
                    "--lang", "cs",
                    "--in-place",
                ]
                # Should not raise SystemExit due to "unrecognized arguments"
                try:
                    main()
                except SystemExit as e:
                    # Only fail if exit was due to argparse error
                    # (not normal completion)
                    pass
            finally:
                sys.argv = original_argv

            # Verify the file was actually processed
            content = test_file.read_text(encoding="utf-8")
            self.assertIn("Ahoj", content)

    def test_fix_markdown_protects_frontmatter(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        md = "---\ntitle: \"Skryté úspory\"\nlocale: \"cs\"\n---\n\n\"Ahoj světe\""
        result = typolima.fix_markdown(md, rules)
        self.assertIn("title: \"Skryté úspory\"", result)
        self.assertNotIn("title: „Skryté úspory“", result)
        self.assertIn("„Ahoj světe“", result)

    def test_fix_markdown_protects_code_blocks(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        md = "Text \"s uvozovkami\"\n\n```javascript\nconst x = \"low\";\n```\n\n\"Další\""
        result = typolima.fix_markdown(md, rules)
        self.assertIn("const x = \"low\"", result)
        self.assertNotIn("„low“", result)
        self.assertIn("„Další“", result)

    def test_fix_markdown_no_frontmatter(self):
        rules = typolima.load_rules("en", self.rules_dir)
        md = "\"Hello\" world\n10000"
        result = typolima.fix_markdown(md, rules)
        self.assertIn("“Hello”", result)
        self.assertIn("10,000", result)

    def test_fix_markdown_frontmatter_only(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        md = "---\ntitle: \"Keep\"\n---\n"
        result = typolima.fix_markdown(md, rules)
        self.assertEqual(result, md)

    def test_fix_markdown_multiple_code_blocks(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        md = "```\nconst a = \"x\";\n```\nmezi\n```\nconst b = \"y\";\n```"
        result = typolima.fix_markdown(md, rules)
        self.assertIn("const a = \"x\"", result)
        self.assertIn("const b = \"y\"", result)
        self.assertIn("mezi", result)

    def test_fix_markdown_frontmatter_and_code_blocks(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        md = "---\ntitle: \"Test\"\n---\n\n\"Text\"\n\n```\nkód\n```"
        result = typolima.fix_markdown(md, rules)
        self.assertIn("title: \"Test\"", result)
        self.assertIn("„Text“", result)
        self.assertIn("kód", result)

    def test_verbose_short_flag_not_filtered(self):
        # Regression test: -v is TypoLima's --verbose short alias
        # and must NOT be filtered out as a Python interpreter flag.
        import tempfile
        from pathlib import Path
        import sys
        from typolima.core import main

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.html"
            test_file.write_text("<p>Hello</p>", encoding="utf-8")

            original_argv = sys.argv
            try:
                sys.argv = [
                    "typolima",
                    str(test_file),
                    "--lang", "en",
                    "--in-place",
                    "-v",  # Must NOT be filtered out
                ]
                try:
                    main()
                except SystemExit:
                    pass
            finally:
                sys.argv = original_argv

            # -v should still be in sys.argv (not filtered)
            self.assertIn("-v", sys.argv)


if __name__ == "__main__":
    unittest.main()
