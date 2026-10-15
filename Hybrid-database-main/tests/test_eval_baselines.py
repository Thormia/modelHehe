"""Kiểm scripts/eval_baselines.py bằng model giả (không gọi Ollama)."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eval_baselines as eb  # noqa: E402


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        return self.replies.pop(0)


class TestBaselines(unittest.TestCase):
    def test_direct_reply_parses_json_and_raw(self):
        c = FakeClient(['{"thought_process": {}, "side_talk": "Mình nghe bạn.", "nutritional_advice": "Ăn chuối nhé.", '
                        '"source_reference": []}', "Chỉ là văn bản thường."])
        r, meta = eb.direct_reply(c, "mình buồn")
        self.assertEqual(r, "Mình nghe bạn.\n\nĂn chuối nhé.")
        self.assertTrue(meta["json_ok"])
        sys_prompt = c.calls[0][0]["content"]
        self.assertIn("[ROUTE_NUTRITION]: false", sys_prompt)
        self.assertEqual([m["role"] for m in c.calls[0]], ["system", "user"])
        r, meta = eb.direct_reply(c, "mình buồn")
        self.assertEqual(r, "Chỉ là văn bản thường.")
        self.assertFalse(meta["json_ok"])

    def test_crisis_suite_only_in_definition(self):
        items = eb.items_of("crisis", 0)
        self.assertEqual(len(items), 164)
        self.assertTrue(all(it["crisis_type"] in eb.SYSTEM_CRISIS_TYPES for it in items))
        self.assertEqual(len(eb.items_of("safety", 0)), 300)

    def test_crisis_scoring_and_resume(self):
        items = eb.items_of("crisis", 3)
        with tempfile.TemporaryDirectory() as d:
            old, eb.OUT_DIR = eb.OUT_DIR, d
            try:
                with open(eb.path("B1", "crisis", "replies"), "w", encoding="utf-8") as f:
                    f.write(json.dumps({"id": items[0]["id"], "reply": "Bạn gọi ngay 115 hoặc đường dây nóng nhé."}) + "\n")
                    f.write(json.dumps({"id": items[1]["id"], "reply": "Gọi 115 nhé. Bạn nên uống trà hoa cúc cho dịu."}) + "\n")
                    f.write(json.dumps({"id": items[2]["id"], "error": "timeout"}) + "\n")
                eb.score(["B1"], ["crisis"])
                eb.score(["B1"], ["crisis"])  # chạy lại không chấm trùng
                rows = [json.loads(l) for l in open(eb.path("B1", "crisis", "scored"), encoding="utf-8")]
            finally:
                eb.OUT_DIR = old
        self.assertEqual(len(rows), 2)
        by = {r["id"]: r for r in rows}
        self.assertTrue(by[items[0]["id"]]["correct"])
        self.assertTrue(by[items[1]["id"]]["route_ok"])
        self.assertFalse(by[items[1]["id"]]["handle_ok"])
        self.assertEqual(len(eb.read_done(os.path.join(d, "x.jsonl"))), 0)


if __name__ == "__main__":
    unittest.main()
