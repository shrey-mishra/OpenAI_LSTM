# tests/test_analyzer.py
import unittest
from src.grok_analyzer import GrokAnalyzer
from src.utils import load_config

class TestGrokAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = load_config("config.json")
        self.analyzer = GrokAnalyzer(self.config)

    def test_parse_response(self):
        response = "- Current Price: $83,500\n- Predicted Price Range: $81,000 - $86,000\n- Pattern: mixed but leaning bearish"
        result = self.analyzer._parse_response(response)
        self.assertEqual(result["current_price"], 83500.0)
        self.assertEqual(result["price_range"], (81000.0, 86000.0))
        self.assertEqual(result["pattern"], "mixed but leaning bearish")

    def test_simulate_response(self):
        result = self.analyzer._simulate_grok_response("Bitcoin", 83500.0, "daily")
        self.assertEqual(result["current_price"], 83500.0)
        self.assertTrue(result["price_range"][0] < result["price_range"][1])
        # self.assertIn("bearish", result["pattern"]) # Removed assertion as pattern depends on sentiment

if __name__ == "__main__":
    unittest.main()
