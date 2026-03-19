import unittest
from pathlib import Path
import sys
import os

# Add project root to path to import typolima
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import typolima.core as typolima

class TestURLFix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Point to the rules directory in the package
        cls.rules_dir = Path(__file__).parent.parent / "typolima" / "rules"

    def test_url_no_split(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        # The issue reported by the user
        text = "explorer.pgarachne.com"
        fixed = typolima.fix_text(text, rules)
        self.assertEqual(fixed, "explorer.pgarachne.com")

    def test_url_with_protocol_no_split(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        text = "https://explorer.pgarachne.com"
        fixed = typolima.fix_text(text, rules)
        self.assertEqual(fixed, "https://explorer.pgarachne.com")

    def test_normal_sentence_split(self):
        rules = typolima.load_rules("cs", self.rules_dir)
        # This is what the rule was intended for (missing space after period)
        text = "Věta.Další věta."
        fixed = typolima.fix_text(text, rules)
        self.assertEqual(fixed, "Věta. Další věta.")

if __name__ == "__main__":
    unittest.main()
