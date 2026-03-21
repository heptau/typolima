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

if __name__ == "__main__":
    unittest.main()
