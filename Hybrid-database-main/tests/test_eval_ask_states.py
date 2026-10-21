import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from eval_ask_states import parse_verdict, questions_of  # noqa: E402


class QuestionsOf(unittest.TestCase):
    def test_question_mark_and_invite(self):
        r = "Mình hiểu bạn đang mệt. Dạo này bạn ngủ thế nào? Nếu được thì kể mình nghe thêm nhé."
        self.assertEqual(questions_of(r), ["Dạo này bạn ngủ thế nào?", "Nếu được thì kể mình nghe thêm nhé."])

    def test_no_question(self):
        self.assertEqual(questions_of("Giấc ngủ rất quan trọng. Bạn nên nghỉ ngơi sớm."), [])


class ParseVerdict(unittest.TestCase):
    MISSING = ["sleep_state", "mood_state"]

    def test_full(self):
        self.assertEqual(parse_verdict('{"reason": "x", "giấc ngủ": true, "tâm trạng": false}', self.MISSING), ["sleep_state"])

    def test_absent_key_is_false(self):
        self.assertEqual(parse_verdict('{"reason": "x", "tâm trạng": true}', self.MISSING), ["mood_state"])

    def test_only_listed_states(self):
        self.assertEqual(parse_verdict('{"reason": "x", "ăn uống": true}', self.MISSING), [])

    def test_bad(self):
        self.assertIsNone(parse_verdict("không phải JSON", self.MISSING))
        self.assertIsNone(parse_verdict('{"reason": "x", "giấc ngủ": "có"}', self.MISSING))


if __name__ == "__main__":
    unittest.main()
