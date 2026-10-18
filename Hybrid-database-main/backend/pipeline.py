"""Luồng mỗi lượt (idea.docx):

LLM #1 + bộ keyword (song song)
 -> cờ khủng hoảng: phản hồi soạn sẵn, không gọi LLM #2
 -> cờ hoảng loạn cấp: phản hồi soạn sẵn (ổn định nhịp thở, 115/113), không gọi LLM #2
 -> cờ thuốc:            Nhánh 1 (medication) ROUTE false + SYSTEM_OVERRIDE         (nhóm B3)
 -> chưa đủ 4 states:    Nhánh 2 (ask_states) ROUTE false + MISSING_STATES          (nhóm B1, B4)
 -> đủ 4 states:         Nhánh 3 (nutrition)  SQL + pgvector, ROUTE true            (nhóm B2)
 -> đã gợi ý, states không đổi: side_talk thuần                                     (nhóm A)
LLM #2 -> Guardrail tầng 1 -> Guardrail tầng 2 (retry tối đa MAX_RETRIES rồi fallback) -> người dùng
"""
import copy
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from . import config, safety
from .constants import STATES
from .guardrails import FALLBACK_REPLY, check_tier1, repair
from .llm import LLMError
from .prompting import build_messages, build_system_prompt


class TurnLogger:
    def __init__(self, path):
        self.path = path
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)

    def write(self, rec):
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class ChatPipeline:
    def __init__(self, generator, extractor, retriever, store, judge=None, logger=None,
                 max_retries=config.MAX_RETRIES, history_turns=config.HISTORY_TURNS,
                 nutrition_top_k=config.NUTRITION_TOP_K, cbt_enabled=config.CBT_ENABLED):
        self.generator, self.extractor, self.retriever, self.store = generator, extractor, retriever, store
        self.judge, self.logger = judge, logger or TurnLogger(None)
        self.max_retries, self.history_turns = max_retries, history_turns
        self.nutrition_top_k, self.cbt_enabled = nutrition_top_k, cbt_enabled
        self._pool = ThreadPoolExecutor(max_workers=4)

    # ------------------------------------------------------------------
    def handle(self, session_id, message):
        t0 = time.time()
        sess = self.store.get(session_id)
        history = sess["history"]
        trace = {"id": uuid.uuid4().hex, "session_id": session_id, "turn": sess["turn"] + 1,
                 "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "user": message}

        # 1. LLM #1 và bộ keyword chạy song song (keyword thuốc vẫn bật cờ thuốc trực tiếp)
        fut = self._pool.submit(self.extractor.extract, history + [{"role": "user", "content": message}])
        kw = safety.scan(message)
        ext = fut.result()
        trace["keywords"] = vars(kw)
        trace["extractor"] = {"ok": ext.ok, "raw": ext.raw}

        # 2. Khủng hoảng: phản hồi soạn sẵn. LLM #1 quyết định (crisis_flag); keyword chỉ ghi vào trace,
        #    và chỉ dùng làm dự phòng khi LLM #1 lỗi (không trả được JSON)
        if ext.crisis_flag or (not ext.ok and kw.crisis):
            reply = safety.crisis_response(panic=ext.panic_flag)
            sess["medication"] = sess["medication"] or kw.medication or ext.medication_alert
            return self._finish(session_id, sess, message, reply, "crisis", trace, t0, obj=None)
        if ext.panic_flag:
            reply = safety.panic_response()
            sess["medication"] = sess["medication"] or kw.medication or ext.medication_alert
            return self._finish(session_id, sess, message, reply, "panic", trace, t0, obj=None)

        # BẢN THỬ NGHIỆM: lớp kiểm tra khủng hoảng thứ hai. Giám khảo (lượt gọi riêng, không đổi prompt guardrail cũ)
        # xét người dùng có ý định tự sát, tự hại hoặc đang gặp nguy hiểm cần giúp gấp mà LLM #1 bỏ sót không.
        if self.judge is not None and hasattr(self.judge, "danger"):
            d = self.judge.danger(history, message)
            trace["danger_check"] = {"ok": d.ok, "user_in_danger": d.in_danger, "reason": d.reason}
            if d.in_danger:
                sess["medication"] = sess["medication"] or kw.medication or ext.medication_alert
                return self._finish(session_id, sess, message, safety.crisis_response(), "crisis_judge", trace, t0, obj=None)

        # 3. Gộp states vào session (giá trị mới ghi đè, null giữ giá trị cũ)
        for s in STATES:
            if ext.states.get(s):
                sess["states"][s] = ext.states[s]
        sess["medication"] = sess["medication"] or kw.medication or ext.medication_alert
        missing = [s for s in STATES if not sess["states"][s]]
        trace["states"], trace["medication"] = dict(sess["states"]), sess["medication"]

        # 4. Định tuyến
        foods, spec = [], None
        if sess["medication"]:
            branch, spec = "medication", dict(route=False, override=True)
        elif missing:
            branch, spec = "ask_states", dict(route=False, missing_states=missing)
        elif sess["last_suggested_states"] == sess["states"]:
            branch, spec = "side_talk", dict(route=False)
        else:
            branch = "nutrition"
            try:
                foods = self.retriever.nutrition(sess["states"], sess["suggested_codes"], self.nutrition_top_k)
            except Exception as e:
                trace["retrieval_error"] = repr(e)
            if foods:
                cbt = None
                if self.cbt_enabled:
                    try:
                        users = [m["content"] for m in history if m["role"] == "user"][-2:] + [message]
                        cbt = self.retriever.cbt(" ".join(users))
                    except Exception as e:
                        trace["cbt_error"] = repr(e)
                spec = dict(route=True, missing_states=[], cbt_context=cbt, nutrition_context=[f["line"] for f in foods])
            else:
                branch, spec = "side_talk", dict(route=False)

        # 5. LLM #2 + Guardrail
        obj, branch, spec = self._generate(history, message, branch, spec, trace)
        if obj is None:
            reply = FALLBACK_REPLY
        else:
            reply = obj["side_talk"]
            if obj.get("nutritional_advice"):
                reply += "\n\n" + obj["nutritional_advice"]
                sess["suggested_codes"] = list(dict.fromkeys(sess["suggested_codes"] + obj["source_reference"]))
                sess["last_suggested_states"] = dict(sess["states"])
        return self._finish(session_id, sess, message, reply, branch, trace, t0, obj=obj,
                            assistant_history=obj["side_talk"] if obj else reply)

    # ------------------------------------------------------------------
    def _generate(self, history, message, branch, spec, trace):
        attempts, last_obj = [], None
        for attempt in range(1 + self.max_retries):
            system = build_system_prompt(**spec)
            # Mã được phép trích: các dòng NUT_ và (nếu có) kỹ thuật trong CBT_CONTEXT, như dữ liệu B2
            codes = {line.split(" – ", 1)[0] for line in (spec.get("nutrition_context") or [])}
            if spec.get("cbt_context"):
                codes.add(spec["cbt_context"].split(" – ", 1)[0])
            rec = {"branch": branch, "system_prompt": system}
            attempts.append(rec)
            try:
                raw = self.generator.chat(build_messages(system, history, message, self.history_turns),
                                          temperature=config.GEN_TEMPERATURE, max_tokens=config.GEN_MAX_TOKENS)
            except LLMError as e:
                rec["error"] = str(e)
                continue
            obj, errs = check_tier1(raw, spec["route"], codes)
            rec.update(raw=raw, tier1=errs)
            if obj is not None and not {"side_talk_empty", "not_json", "non_vietnamese_script"} & set(errs):
                last_obj = (obj, spec, codes)
            if errs:
                continue
            if self.judge is not None:
                v = self.judge.judge(history, message, obj, spec["route"])
                rec["tier2"] = {"ok": v.ok, "flags": v.flags, "retry": v.retry, "block_nutrition": v.block_nutrition,
                                "reason": v.reason}
                if v.block_nutrition:
                    # Bỏ phần gợi ý thực phẩm: sinh lại ở chế độ side_talk (ROUTE false)
                    branch, spec, last_obj = "nutrition_blocked", dict(route=False), None
                    continue
                if v.retry:
                    continue
            trace["attempts"] = attempts
            return obj, branch, spec
        trace["attempts"] = attempts
        if last_obj is not None:
            obj, spec_used, codes = last_obj
            trace["fallback"] = "repair"
            return repair(obj, spec_used["route"], codes), branch, spec_used
        trace["fallback"] = "canned"
        return None, branch, spec

    def _finish(self, session_id, sess, message, reply, branch, trace, t0, obj, assistant_history=None):
        sess["history"] += [{"role": "user", "content": message},
                            {"role": "assistant", "content": assistant_history or reply}]
        sess["turn"] += 1
        self.store.save(session_id, sess)
        result = {"session_id": session_id, "reply": reply, "branch": branch, "states": dict(sess["states"]),
                  "medication": sess["medication"], "output": obj, "latency_s": round(time.time() - t0, 2)}
        trace.update(branch=branch, reply=reply, output=copy.deepcopy(obj), latency_s=result["latency_s"])
        self.logger.write(trace)
        return result


def build_default_pipeline():
    """Pipeline thật: Ollama/vLLM + PostgreSQL + Redis theo cấu hình .env."""
    from .extractor import Extractor
    from .guardrails import Judge
    from .llm import LLMClient
    from .session import make_store
    from retrieval.state_retriever import OfflineStateRetriever, StateRetriever

    gen = LLMClient(config.GEN_BASE_URL, config.GEN_MODEL, config.GEN_API_KEY, config.LLM_TIMEOUT)
    ext = Extractor(LLMClient(config.EXT_BASE_URL, config.EXT_MODEL, config.EXT_API_KEY, config.LLM_TIMEOUT),
                    config.EXT_HISTORY_TURNS)
    judge = Judge(LLMClient(config.JUDGE_BASE_URL, config.JUDGE_MODEL, config.JUDGE_API_KEY, config.LLM_TIMEOUT)) \
        if config.GUARDRAIL_L2_ENABLED else None
    retriever = OfflineStateRetriever() if config.RETRIEVER == "offline" else         StateRetriever(cbt_min_similarity=config.CBT_MIN_SIMILARITY)
    return ChatPipeline(gen, ext, retriever, make_store(config.SESSION_TTL_SECONDS),
                        judge=judge, logger=TurnLogger(config.TURN_LOG_PATH))
