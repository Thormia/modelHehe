"""Kiểm scripts/eval_grounding.py bằng dữ liệu thật của tập test fine-tune và giám khảo giả (không gọi Ollama)."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eval_grounding as eg  # noqa: E402


class FakeJudge:
    def __init__(self, verdict):
        self.verdict = verdict

    def chat(self, messages, **kw):
        return json.dumps(self.verdict)


@unittest.skipUnless(os.path.isdir(eg.TRAINDATA), "không có thư mục traindata")
class TestGrounding(unittest.TestCase):
    def test_gold_labels(self):
        self.assertEqual(len(eg.load_group("B2")), 240)
        self.assertTrue(all(eg.gold_branch(r["messages"][0]["content"]) == "nutrition" for r in eg.load_group("B2")))
        self.assertTrue(all(eg.gold_branch(r["messages"][0]["content"]) == "medication" for r in eg.load_group("B3")))
        b1 = eg.load_group("B1")[0]["messages"][0]["content"]
        self.assertEqual(eg.gold_branch(b1), "ask_states")
        self.assertEqual(eg.gold_missing(b1), ["appetite_state", "mood_state"])

    def test_context_and_training_answer_is_grounded(self):
        r = eg.load_group("B2")[0]
        nut, codes = eg.context_lines(r["messages"][0]["content"])
        self.assertTrue(nut and all(l.startswith("NUT_") for l in nut))
        self.assertIn("NUT_095", codes)
        self.assertTrue(any(c.startswith("PSY_") for c in codes))
        ok = eg._grounding(r["messages"][-1]["content"], nut, codes,
                           FakeJudge({"reason": "", "unsupported_claim": False, "foreign_food": False}))
        self.assertTrue(ok["grounded"], ok)
        bad = json.loads(r["messages"][-1]["content"])
        bad["source_reference"] = ["NUT_999"]
        bad["nutritional_advice"] += " Bạn ăn thêm cá hồi 200 g nhé."
        res = eg._grounding(json.dumps(bad, ensure_ascii=False), nut, codes,
                            FakeJudge({"reason": "", "unsupported_claim": True, "foreign_food": True}))
        self.assertFalse(res["grounded"])
        self.assertFalse(res["refs_in_context"])
        self.assertFalse(res["no_quantity"])

    def test_score_part_b_branch_and_missing(self):
        r = eg.load_group("B1")[0]
        run = {"id": r["id"], "group": "B1", "gold_branch": "ask_states", "gold_missing": ["appetite_state", "mood_state"],
               "n_turns": 2, "turns": [
                   {"branch": "ask_states", "states": {}, "context_nut": [], "context_codes": []},
                   {"branch": "ask_states", "states": {"sleep_state": "Poor", "stress_state": "High"},
                    "context_nut": [], "context_codes": []}]}
        with tempfile.TemporaryDirectory() as d:
            old, old_client, eg.OUT_DIR = eg.OUT_DIR, eg.LLMClient, d
            try:
                with open(eg.path("B_B1_runs.jsonl"), "w", encoding="utf-8") as f:
                    f.write(json.dumps(run) + "\n")
                eg.LLMClient = lambda *a, **k: FakeJudge({})
                eg.score()
                rec = json.loads(open(eg.path("B_B1_scored.jsonl"), encoding="utf-8").readline())
            finally:
                eg.OUT_DIR, eg.LLMClient = old, old_client
        self.assertTrue(rec["branch_ok"])
        self.assertTrue(rec["missing_exact"])
        self.assertEqual((rec["known_tp"], rec["known_fp"], rec["known_fn"]), (2, 0, 0))


if __name__ == "__main__":
    unittest.main()
