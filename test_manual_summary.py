import unittest
from types import SimpleNamespace

from src.manual_summary import deterministic_summary, summarize_manual_results


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        msg = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeClient:
    def __init__(self, content):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


class ManualSummaryTests(unittest.TestCase):
    def setUp(self):
        self.results = {
            "glucose": "neg.",
            "protein": "+30(0.3)",
            "ph": "6",
        }

    def test_deterministic_fallback_preserves_values(self):
        out = deterministic_summary(self.results)
        self.assertFalse(out["ai_used"])
        self.assertIn("Glucose: neg.", out["summary"])
        self.assertIn("Protein: +30(0.3)", out["summary"])

    def test_ai_json_summary_is_used(self):
        client = FakeClient('{"summary":"สรุปจากค่าที่เลือก","bullets":["ควรตรวจทาน"]}')
        out = summarize_manual_results(self.results, client=client, model="fake-model")
        self.assertTrue(out["ai_used"])
        self.assertEqual(out["summary"], "สรุปจากค่าที่เลือก")
        self.assertEqual(out["bullets"], ["ควรตรวจทาน"])

    def test_malformed_ai_falls_back(self):
        client = FakeClient("not json")
        out = summarize_manual_results(self.results, client=client, model="fake-model")
        self.assertFalse(out["ai_used"])
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
