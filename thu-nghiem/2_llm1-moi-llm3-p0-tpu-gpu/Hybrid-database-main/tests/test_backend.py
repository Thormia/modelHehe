"""Test backend với LLM / database giả lập (không cần Ollama, Docker).

    python -m unittest discover -s tests -v      (từ thư mục Hybrid-database-main)
"""
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import safety  # noqa: E402
from backend.constants import FIXED_PROMPT, STATES, SYSTEM_OVERRIDE  # noqa: E402
from backend.extractor import Extraction, Extractor  # noqa: E402
from backend.guardrails import Verdict, check_tier1, repair  # noqa: E402
from backend.llm import parse_json_object  # noqa: E402
from backend.pipeline import ChatPipeline  # noqa: E402
from backend.prompting import build_messages, build_system_prompt  # noqa: E402
from backend.session import MemoryStore  # noqa: E402
from retrieval.state_retriever import format_nutrition_line, nut_code  # noqa: E402

TRAINDATA = os.path.join(os.path.dirname(ROOT), "traindata")
with open(os.path.join(ROOT, "data", "processed", "400 data dinh duong.json"), encoding="utf-8") as _f:
    FOODS = json.load(_f)


def out(route, side_talk="Mình hiểu cảm giác của bạn.", advice=None, refs=None):
    return json.dumps({"thought_process": {"detected_emotions": "Mệt mỏi", "detected_symptoms": [], "trigger_nutrition": route,
                                           "reasoning": f"ROUTE_NUTRITION = {'true' if route else 'false'}. ..."},
                       "side_talk": side_talk, "nutritional_advice": advice, "source_reference": refs or []},
                      ensure_ascii=False)


# ---------------- Định dạng prompt phải trùng với dữ liệu train ----------------
def parse_blocks(system):
    rest = system[len(FIXED_PROMPT) + 2:]
    parts = re.split(r"^\[([A-Z_]+)\]:", rest, flags=re.M)
    return {k: v.strip() for k, v in zip(parts[1::2], parts[2::2])}


@unittest.skipUnless(os.path.isdir(TRAINDATA), "không có thư mục traindata")
class TestPromptMatchesTraining(unittest.TestCase):
    def test_rebuild_every_training_system_prompt(self):
        n = 0
        for fn in glob.glob(os.path.join(TRAINDATA, "*_*_*.jsonl")):  # group_*/test_* (bỏ safetyguard.jsonl)
            with open(fn, encoding="utf-8") as fh:
                lines = [l for l in fh if l.strip()]
            for line in lines:
                system = json.loads(line)["messages"][0]["content"]
                b = parse_blocks(system)
                rebuilt = build_system_prompt(
                    route=b["ROUTE_NUTRITION"] == "true",
                    missing_states=json.loads(b["MISSING_STATES"]) if "MISSING_STATES" in b else None,
                    override="SYSTEM_OVERRIDE" in b,
                    cbt_context=None if b["CBT_CONTEXT"] == "None" else b["CBT_CONTEXT"],
                    nutrition_context=None if b["NUTRITION_CONTEXT"] == "None" else b["NUTRITION_CONTEXT"].splitlines())
                self.assertEqual(rebuilt, system, fn)
                n += 1
        self.assertGreater(n, 1000)

    def test_override_constant_matches_training(self):
        with open(os.path.join(TRAINDATA, "group_B_B3.jsonl"), encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
        self.assertIn(SYSTEM_OVERRIDE, rows[0]["messages"][0]["content"])

    def test_training_answers_pass_tier1(self):
        # Câu trả lời mẫu trong dữ liệu train phải qua tầng 1 với cùng tập mã mà pipeline cho phép (NUT_ + mã CBT)
        n = cjk = 0
        for fn in glob.glob(os.path.join(TRAINDATA, "group_B_*.jsonl")):
            with open(fn, encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    msgs = json.loads(line)["messages"]
                    b = parse_blocks(msgs[0]["content"])
                    codes = set() if b["NUTRITION_CONTEXT"] == "None" else \
                        {l.split(" – ", 1)[0] for l in b["NUTRITION_CONTEXT"].splitlines()}
                    if b["CBT_CONTEXT"] != "None":
                        codes.add(b["CBT_CONTEXT"].split(" – ", 1)[0])
                    _, errs = check_tier1(msgs[-1]["content"], b["ROUTE_NUTRITION"] == "true", codes)
                    self.assertNotIn("ref_not_in_context", errs, fn)
                    self.assertNotIn("nut_ref_missing", errs, fn)
                    cjk += "non_vietnamese_script" in errs
                    n += 1
        self.assertGreater(n, 500)
        self.assertLessEqual(cjk, 1)  # group_B_B1.jsonl có sẵn 1 câu lẫn chữ Hán ("căng脑"), lỗi của dữ liệu


class TestNutritionLine(unittest.TestCase):
    def line(self, i):
        f = FOODS[i - 1]
        return format_nutrition_line(nut_code(i), f["food_item"], f["key_nutrients"], f["ontology_effect"], f["content_text"])

    def test_same_format_as_training(self):
        # Dòng thật trong group_B_B2.jsonl
        self.assertEqual(self.line(306), "NUT_306 – Hải sâm | Tryptophan | REGULATING | điều hòa dẫn truyền thần kinh")

    def test_primary_nutrient_full_name(self):
        # content_text viết "Long-chain Omega-3", key_nutrients viết đầy đủ "Long-chain Omega-3 (EPA+DHA)" như dữ liệu train
        f = next(i for i, x in enumerate(FOODS, 1) if (x["content_text"] or "").count("Long-chain Omega-3 có tác dụng"))
        self.assertIn("| Long-chain Omega-3 (EPA+DHA) |", self.line(f))


# ---------------- Guardrail tầng 1 ----------------
class TestTier1(unittest.TestCase):
    def test_valid_false(self):
        o, errs = check_tier1(out(False, "Dạo này chuyện ăn uống của bạn thế nào?"), False, set())
        self.assertEqual(errs, [])  # hỏi thăm ăn uống là hợp lệ

    def test_food_suggestion_when_false(self):
        _, errs = check_tier1(out(False, "Bạn hãy thử uống một ly sữa ấm trước khi ngủ nhé."), False, set())
        self.assertIn("food_suggestion_when_route_false", errs)

    def test_advice_when_false(self):
        _, errs = check_tier1(out(False, advice="Ăn hải sâm", refs=["NUT_306"]), False, set())
        self.assertIn("advice_when_route_false", errs)

    def test_ref_not_in_context_and_quantity(self):
        _, errs = check_tier1(out(True, advice="Ăn 100 g hải sâm", refs=["NUT_999"]), True, {"NUT_306"})
        self.assertIn("ref_not_in_context", errs)
        self.assertIn("quantity_in_advice", errs)

    def test_trigger_mismatch_and_not_json(self):
        _, errs = check_tier1(out(True, advice="Hải sâm", refs=["NUT_306"]), False, set())
        self.assertIn("trigger_ne_route", errs)
        self.assertEqual(check_tier1("xin chào", False, set()), (None, ["not_json"]))

    def test_cbt_ref_needs_nut_ref(self):
        codes = {"NUT_306", "PSY_CBT_0052"}
        _, errs = check_tier1(out(True, advice="Hải sâm", refs=["PSY_CBT_0052", "NUT_306"]), True, codes)
        self.assertEqual(errs, [])
        _, errs = check_tier1(out(True, advice="Hải sâm", refs=["PSY_CBT_0052"]), True, codes)
        self.assertIn("nut_ref_missing", errs)

    def test_chinese_text_rejected_and_cut_by_repair(self):
        st = "Mình hiểu bạn đang mệt. Bạn thử nghe nhạc nhé. Những việc看上去你正在经历一段艰难的时期。"
        _, errs = check_tier1(out(False, st), False, set())
        self.assertIn("non_vietnamese_script", errs)
        o = repair(json.loads(out(False, st)), False, set())
        self.assertEqual(o["side_talk"], "Mình hiểu bạn đang mệt. Bạn thử nghe nhạc nhé.")

    def test_parse_json_with_fences(self):
        self.assertEqual(parse_json_object('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(parse_json_object('Đây: {"a": {"b": 2}} xong'), {"a": {"b": 2}})

    def test_repair_drops_invalid_advice(self):
        o = repair(json.loads(out(True, "Mình hiểu. Bạn nên uống trà gừng.", "Ăn 50 g hải sâm", ["NUT_306"])), True, {"NUT_306"})
        self.assertIsNone(o["nutritional_advice"])
        o = repair(json.loads(out(False, "Mình hiểu bạn. Bạn hãy thử uống trà gừng nhé.")), False, set())
        self.assertEqual(o["side_talk"], "Mình hiểu bạn.")


class TestSafetyKeywords(unittest.TestCase):
    def test_crisis(self):
        self.assertTrue(safety.scan("chắc mình đi cho xong để mọi người nhẹ nợ").crisis)
        self.assertFalse(safety.scan("hôm nay mệt chết đi được").crisis)  # nói quá: để LLM #1 quyết

    def test_medication(self):
        self.assertTrue(safety.scan("mình đang tiêm kích trứng").medication)
        self.assertTrue(safety.scan("bác sĩ kê thuốc ngủ cho mình").medication)
        self.assertFalse(safety.scan("mình đang cố bỏ thuốc lá").medication)


# ---------------- Pipeline với thành phần giả ----------------
class FakeLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        return self.replies.pop(0)


class FakeExtractor:
    def __init__(self, seq):
        self.seq = list(seq)

    def extract(self, history):
        states, med, crisis = self.seq.pop(0)
        return Extraction(states={s: states.get(s) for s in STATES}, medication_alert=med, crisis_flag=crisis)


class FakeRetriever:
    def nutrition(self, states, exclude_codes=(), k=1):
        code = "NUT_306" if "NUT_306" not in exclude_codes else "NUT_336"
        return [{"code": code, "food_item": "x", "line": f"{code} – Hải sâm | Tryptophan | REGULATING | điều hòa dẫn truyền thần kinh"}]

    def cbt(self, text):
        return "PSY_MINDFUL_0001 – Nhận thức hơi thở (Breath Awareness) | Quan sát và nhận diện nhịp thở vào và thở ra tự nhiên để định tâm"


class FakeChecker:
    def __init__(self, verdicts=None):
        self.verdicts, self.calls = list(verdicts or []), []

    def check(self, history, msg, o, route, branch, missing_states=None):
        self.calls.append((branch, missing_states))
        return self.verdicts.pop(0) if self.verdicts else Verdict(ok=True)


FULL = {"sleep_state": "Poor", "appetite_state": "Low", "stress_state": "High", "mood_state": "Stressed"}


def make(ext_seq, gen_replies, checker=None):
    gen = FakeLLM(gen_replies)
    return ChatPipeline(gen, FakeExtractor(ext_seq), FakeRetriever(), MemoryStore(), checker=checker or FakeChecker()), gen


class TestPipeline(unittest.TestCase):
    def test_crisis_skips_generator(self):
        p, gen = make([({}, False, True)], [])
        r = p.handle("s", "mình không muốn tỉnh dậy nữa")
        self.assertEqual(r["branch"], "crisis")
        self.assertEqual(gen.calls, [])
        self.assertIn("115", r["reply"])

    def test_keyword_alone_does_not_trigger_crisis(self):
        p, gen = make([({}, False, False)], ['{"trigger": false, "side_talk": "Mình nghe bạn. Bạn muốn kể thêm không?"}'] * 3)
        r = p.handle("s", "năm ngoái mình từng nghĩ tới chuyện tự tử, giờ ổn rồi")
        self.assertNotEqual(r["branch"], "crisis")

    def test_keyword_is_fallback_when_extractor_fails(self):
        p, gen = make([], [])
        p.extractor = type("E", (), {"extract": lambda self, h: Extraction(ok=False)})()
        r = p.handle("s", "mình muốn tự tử")
        self.assertEqual(r["branch"], "crisis")
        self.assertEqual(gen.calls, [])

    def test_crisis_response_covers_panic_and_self_harm(self):
        p, gen = make([({}, False, True)], [])
        r = p.handle("s", "tim mình đập loạn, không thở được, sợ ngất ngay đây")
        self.assertEqual(r["branch"], "crisis")
        self.assertEqual(gen.calls, [])
        self.assertIn("làm hại bản thân", r["reply"])
        self.assertIn("thở chậm", r["reply"])

    def test_old_panic_key_still_counts_as_crisis(self):
        ext = Extractor(FakeLLM(['{"sleep_state": null, "panic_flag": true}']))
        self.assertTrue(ext.extract([{"role": "user", "content": "x"}]).crisis_flag)

    def test_ask_states_then_nutrition_then_side_talk(self):
        p, gen = make(
            [({"stress_state": "High"}, False, False), (FULL, False, False), (FULL, False, False)],
            [out(False, "Bạn ngủ thế nào?"),
             out(True, "Mình hiểu.", "Bạn có thể thêm hải sâm vào bữa ăn.", ["NUT_306"]),
             out(False, "Mình vẫn ở đây.")])
        r1 = p.handle("s", "dạo này căng thẳng quá")
        self.assertEqual(r1["branch"], "ask_states")
        self.assertIn('[MISSING_STATES]: ["sleep_state", "appetite_state", "mood_state"]', gen.calls[0][0]["content"])

        r2 = p.handle("s", "mất ngủ, chán ăn, buồn bực")
        self.assertEqual(r2["branch"], "nutrition")
        sysmsg = gen.calls[1][0]["content"]
        self.assertIn("[ROUTE_NUTRITION]: true\n[MISSING_STATES]: []\n[CBT_CONTEXT]: PSY_MINDFUL_0001", sysmsg)
        self.assertIn("[NUTRITION_CONTEXT]:\nNUT_306 – Hải sâm", sysmsg)
        self.assertIn("hải sâm", r2["reply"])
        # lịch sử đưa vào lượt sau chỉ chứa side_talk
        self.assertEqual(gen.calls[1][-2], {"role": "assistant", "content": "Bạn ngủ thế nào?"})

        r3 = p.handle("s", "cảm ơn nhé")
        self.assertEqual(r3["branch"], "side_talk")  # states không đổi sau khi đã gợi ý
        self.assertIn("[ROUTE_NUTRITION]: false\n[CBT_CONTEXT]: None\n[NUTRITION_CONTEXT]: None", gen.calls[2][0]["content"])

    def test_medication_is_sticky_and_overrides(self):
        p, gen = make([(FULL, True, False), (FULL, False, False)], [out(False), out(False)])
        self.assertEqual(p.handle("s", "mình đang uống thuốc an thần")["branch"], "medication")
        self.assertEqual(p.handle("s", "hôm nay ổn hơn")["branch"], "medication")
        self.assertIn("[SYSTEM_OVERRIDE]: " + SYSTEM_OVERRIDE, gen.calls[1][0]["content"])

    def test_tier1_retry_then_repair(self):
        bad = out(False, "Mình hiểu bạn. Bạn hãy thử uống trà gừng nhé.")
        p, gen = make([({"stress_state": "High"}, False, False)], [bad, bad, bad])
        r = p.handle("s", "căng thẳng quá")
        self.assertEqual(len(gen.calls), 3)  # 1 lần + 2 retry
        self.assertEqual(r["reply"], "Mình hiểu bạn.")

    def test_llm3_blocks_nutrition(self):
        checker = FakeChecker([Verdict(ok=True, block_nutrition=True)])
        p, gen = make([(FULL, False, False)],
                      [out(True, "Mình hiểu.", "Thêm hải sâm vào bữa ăn.", ["NUT_306"]), out(False, "Bạn nên đi khám sớm.")],
                      checker=checker)
        r = p.handle("s", "mình mang thai, mất ngủ, chán ăn, căng thẳng")
        self.assertEqual(r["branch"], "nutrition_blocked")
        self.assertEqual(r["reply"], "Bạn nên đi khám sớm.")
        self.assertIn("[ROUTE_NUTRITION]: false", gen.calls[1][0]["content"])

    def test_llm3_missed_crisis_gives_crisis_response(self):
        checker = FakeChecker([Verdict(ok=True, missed_crisis=True)])
        p, gen = make([({"stress_state": "High"}, False, False)], [out(False, "Bạn ngủ thế nào?")], checker=checker)
        r = p.handle("s", "căng thẳng quá")
        self.assertEqual(r["branch"], "crisis_llm3")
        self.assertIn("115", r["reply"])
        self.assertNotIn("Bạn ngủ thế nào?", r["reply"])

    def test_llm3_retry_then_accept(self):
        checker = FakeChecker([Verdict(ok=True, retry=True), Verdict(ok=True)])
        p, gen = make([({"stress_state": "High"}, False, False)], [out(False, "Ừ."), out(False, "Mình hiểu bạn. Bạn ngủ thế nào?")],
                      checker=checker)
        r = p.handle("s", "căng thẳng quá")
        self.assertEqual(len(gen.calls), 2)
        self.assertEqual(r["reply"], "Mình hiểu bạn. Bạn ngủ thế nào?")
        self.assertEqual(checker.calls[0], ("ask_states", ["sleep_state", "appetite_state", "mood_state"]))

    def test_unparsable_output_gives_fallback(self):
        p, gen = make([({}, False, False)], ["???", "???", "???"])
        r = p.handle("s", "chào bạn")
        self.assertIn("Cảm ơn bạn đã chia sẻ", r["reply"])


class TestExtractorNormalization(unittest.TestCase):
    def test_invalid_labels_become_null(self):
        ext = Extractor(FakeLLM(['{"sleep_state": "Poor", "mood_state": "Anxious", "medication_alert": "yes", "crisis_flag": false}']))
        e = ext.extract([{"role": "user", "content": "mất ngủ"}])
        self.assertEqual(e.states["sleep_state"], "Poor")
        self.assertIsNone(e.states["mood_state"])
        self.assertFalse(e.medication_alert)


class TestOfflineRetriever(unittest.TestCase):
    def test_line_format_and_exclusion(self):
        from retrieval.state_retriever import OfflineStateRetriever
        r = OfflineStateRetriever()
        out = r.nutrition(FULL, k=3)
        self.assertEqual(len(out), 3)
        for f in out:
            self.assertRegex(f["line"], r"^NUT_\d{3} – .+ \| .+ \| (INHIBITING|REDUCING|REGULATING) \| .+$")
        self.assertNotIn("NUT_060", [c for c, _ in r.foods])

    def test_stress_high_picks_stress_response(self):
        from retrieval.state_retriever import OfflineStateRetriever
        r = OfflineStateRetriever()
        f = r.nutrition({"sleep_state": "Good", "appetite_state": "Normal", "stress_state": "High", "mood_state": "Calm"})[0]
        self.assertTrue(f["line"].endswith("phản ứng căng thẳng"))

    def test_excludes_already_suggested(self):
        from retrieval.state_retriever import OfflineStateRetriever
        r = OfflineStateRetriever()
        first = r.nutrition(FULL)[0]["code"]
        self.assertNotEqual(r.nutrition(FULL, exclude_codes=[first])[0]["code"], first)


class TestMessages(unittest.TestCase):
    def test_history_window_starts_with_user(self):
        h = [{"role": "user", "content": str(i)} if i % 2 == 0 else {"role": "assistant", "content": str(i)} for i in range(10)]
        msgs = build_messages("SYS", h, "new", history_turns=2)
        self.assertEqual([m["role"] for m in msgs], ["system", "user", "assistant", "user", "assistant", "user"])


if __name__ == "__main__":
    unittest.main()
