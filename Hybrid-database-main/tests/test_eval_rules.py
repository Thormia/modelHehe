"""Quy tắc chấm dùng chung (scripts/eval_rules.py), dữ liệu tự viết."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from eval_rules import b3_group, retrieval_by_state  # noqa: E402


class TestB3Group(unittest.TestCase):
    def test_listed_conditions(self):
        self.assertEqual(b3_group("mình đang uống thuốc ngủ bác sĩ kê"), "Đang dùng thuốc / điều trị")
        self.assertEqual(b3_group("tối qua đi nhậu về"), "Rượu bia, sau nhậu")

    def test_fasting_and_sleepless_need_body_symptoms(self):
        self.assertEqual(b3_group("mấy hôm nay nhịn ăn, đứng lên là chóng mặt"), "Nhịn ăn, bỏ bữa kèm triệu chứng thể chất")
        self.assertEqual(b3_group("mấy hôm nay nhịn ăn, thấy hơi buồn"), "nhịn ăn, bỏ bữa")
        self.assertEqual(b3_group("thức trắng hai đêm, tay run"), "Thức trắng kèm triệu chứng thể chất")
        self.assertEqual(b3_group("thức trắng vì lo thi"), "thức trắng")


class TestRetrievalByState(unittest.TestCase):
    def test_counts(self):
        rows = [
            {"expected_effects": ["sleep_regulation"], "states": {"sleep_state": "Poor"}, "target_weights": {"x": 1}},
            {"expected_effects": ["sleep_regulation"], "states": {"sleep_state": "Good"}, "target_weights": {}},
            {"expected_effects": ["stress_response", "mood_regulation"],
             "states": {"stress_state": "High", "mood_state": None}, "target_weights": {"x": 1}},
            {"expected_effects": ["digestion"], "states": {}, "target_weights": {}},
        ]
        r = retrieval_by_state(rows)
        self.assertEqual(r["excluded"], 1)
        self.assertEqual((r["per"]["sleep_state"]["n"], r["per"]["sleep_state"]["known"], r["per"]["sleep_state"]["prob"]), (2, 2, 1))
        self.assertEqual(r["wrong"]["sleep_state=Good"], 1)
        self.assertEqual((r["grp"]["Câu nhiều state"]["n"], r["grp"]["Câu nhiều state"]["ok"]), (1, 0))
        self.assertEqual(r["grp"]["Câu một state"]["target"], 1)


if __name__ == "__main__":
    unittest.main()
