"""Phân tích chi tiết kết quả final (Output của notebook Kaggle) – không chạy lại model.

    python scripts/analyze_final.py ../eval_final_results      ->  in bảng Markdown, ghi analysis_final.json

Bổ sung cho eval_baselines.py report:
  - Trả lời hợp lệ: câu trả lời do model sinh ra (hoặc phản hồi khủng hoảng / hoảng loạn soạn sẵn theo thiết kế).
    Câu dự phòng FALLBACK_REPLY (pipeline trả khi LLM #2 hỏng định dạng sau mọi lần sinh) tính là KHÔNG hợp lệ.
  - Đạt hiệu quả = đạt tiêu chí an toàn / khủng hoảng VÀ trả lời hợp lệ (không để câu dự phòng làm đẹp số).
  - Tuân thủ định dạng đầu ra, tách theo loại bẫy / loại khủng hoảng, số lần sinh, guardrail, độ trễ (trên Kaggle).
"""
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
SYSTEMS = ["P", "B1", "B2", "B3"]
PIPELINE = {"P", "B3"}
N_SMOKE = 5  # 5 lượt chạy thử đầu tiên trong turns.jsonl


def jl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "–"


def main(root):
    base = os.path.join(root, "logs", "eval", "baselines")
    turns = jl(os.path.join(root, "logs", "turns.jsonl"))
    scored = {(s, su): jl(os.path.join(base, f"{s}_{su}_scored.jsonl")) for s in SYSTEMS for su in ("crisis", "safety")}
    replies = {(s, su): {r["id"]: r for r in jl(os.path.join(base, f"{s}_{su}_replies.jsonl"))}
               for s in SYSTEMS for su in ("crisis", "safety")}
    # Trace: P chạy trước (crisis rồi safety), B3 chạy sau; mỗi hệ thống 164 + 300 lượt
    n = len(scored["P", "crisis"]) + len(scored["P", "safety"])
    assert len(turns) == N_SMOKE + 2 * n, len(turns)
    trace = {"P": turns[N_SMOKE:N_SMOKE + n], "B3": turns[N_SMOKE + n:]}
    out = {}
    for s in SYSTEMS:
        tq = defaultdict(list)
        for t in trace.get(s, []):
            tq[t["user"]].append(t)
        res = {}
        for su in ("crisis", "safety"):
            rows = scored[s, su]
            info = []
            for r in rows:
                if s in PIPELINE:
                    t = tq[r["query"]].pop(0)
                    att = t.get("attempts", [])
                    rec = {"valid": t.get("fallback") != "canned", "fallback": t.get("fallback", "none"),
                           "llm2_called": bool(att), "n_gen": len(att),
                           "fmt_first": bool(att) and not att[0].get("tier1") and "error" not in att[0],
                           "tier2_retry": sum(1 for a in att if (a.get("tier2") or {}).get("retry")),
                           "tier2_block": sum(1 for a in att if (a.get("tier2") or {}).get("block_nutrition")),
                           "latency": t.get("latency_s"), "branch": t.get("branch")}
                else:
                    rp = replies[s, su][r["id"]]
                    rec = {"valid": bool(r["reply"].strip()), "fallback": "none", "llm2_called": True, "n_gen": 1,
                           "fmt_first": bool(rp.get("json_ok")), "tier2_retry": 0, "tier2_block": 0,
                           "latency": None, "branch": None}
                rec["correct"] = r["correct"]
                rec["effective"] = r["correct"] and rec["valid"]
                rec["group"] = r.get("type") or r.get("sub_type")
                if su == "safety":
                    rec["checks"] = r["checks"]
                info.append(rec)
            called = [x for x in info if x["llm2_called"]]
            lat = [x["latency"] for x in info if x["latency"] is not None]
            g = defaultdict(list)
            for x in info:
                g[x["group"]].append(x)
            res[su] = {
                "n": len(info),
                "correct": sum(x["correct"] for x in info),
                "valid": sum(x["valid"] for x in info),
                "effective": sum(x["effective"] for x in info),
                "fallback": dict(Counter(x["fallback"] for x in info)),
                "llm2_called": len(called),
                "fmt_first": sum(x["fmt_first"] for x in called),
                "mean_gen": round(statistics.mean(x["n_gen"] for x in called), 2) if called else None,
                "tier2_retry_cases": sum(1 for x in info if x["tier2_retry"]),
                "tier2_block_cases": sum(1 for x in info if x["tier2_block"]),
                "latency_median": round(statistics.median(lat), 1) if lat else None,
                "latency_p90": round(sorted(lat)[int(0.9 * (len(lat) - 1))], 1) if lat else None,
                "by_group": {k: {"n": len(v), "correct": sum(x["correct"] for x in v),
                                 "effective": sum(x["effective"] for x in v)} for k, v in sorted(g.items())},
            }
            if su == "safety":
                res[su]["checks"] = {k: sum(x["checks"][k] for x in info) for k in info[0]["checks"]}
                res[su]["checks_valid"] = {k: sum(x["checks"][k] and x["valid"] for x in info) for k in info[0]["checks"]}
        out[s] = res
    with open(os.path.join(root, "logs", "eval", "analysis_final.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    show(out)


def show(o):
    S = SYSTEMS
    print("### Tổng hợp\n")
    print("| Chỉ số | " + " | ".join(S) + " |")
    print("|---|" + "---|" * len(S))
    for su, name in (("crisis", "Crisis"), ("safety", "Safety")):
        print(f"| {name}: đạt (chấm tự động, gồm cả câu dự phòng) | " + " | ".join(pct(o[s][su]["correct"], o[s][su]["n"]) for s in S) + " |")
        print(f"| {name}: trả lời hợp lệ (không phải câu dự phòng) | " + " | ".join(pct(o[s][su]["valid"], o[s][su]["n"]) for s in S) + " |")
        print(f"| **{name}: đạt hiệu quả (đạt VÀ trả lời hợp lệ)** | " + " | ".join(f"**{pct(o[s][su]['effective'], o[s][su]['n'])}**" for s in S) + " |")
    for su, name in (("crisis", "Crisis"), ("safety", "Safety")):
        print(f"| {name}: đúng định dạng ngay lần sinh đầu (trên ca có gọi LLM #2) | " + " | ".join(pct(o[s][su]["fmt_first"], o[s][su]["llm2_called"]) for s in S) + " |")
        print(f"| {name}: số lần sinh trung bình | " + " | ".join(str(o[s][su]["mean_gen"]) for s in S) + " |")
    for su in ("crisis", "safety"):
        print(f"| {su}: ca bị guardrail tầng 2 yêu cầu sinh lại | " + " | ".join(str(o[s][su]["tier2_retry_cases"]) if s in PIPELINE else "–" for s in S) + " |")
        print(f"| {su}: độ trễ trung vị / p90 (giây, Kaggle T4×2) | " + " | ".join(f"{o[s][su]['latency_median']} / {o[s][su]['latency_p90']}" if s in PIPELINE else "–" for s in S) + " |")
    print("\n### Safety theo tiêu chí (đạt tự động; trong ngoặc: đạt và trả lời hợp lệ)\n")
    print("| Tiêu chí | " + " | ".join(S) + " |")
    print("|---|" + "---|" * len(S))
    for k in o["P"]["safety"]["checks"]:
        print(f"| {k} | " + " | ".join(f"{o[s]['safety']['checks'][k]} ({o[s]['safety']['checks_valid'][k]})" for s in S) + " |")
    for su, title in (("safety", "Safety theo loại bẫy"), ("crisis", "Crisis theo loại")):
        print(f"\n### {title}: đạt tự động / đạt hiệu quả\n")
        print("| Loại | n | " + " | ".join(S) + " |")
        print("|---|---|" + "---|" * len(S))
        for gname, gv in o["P"][su]["by_group"].items():
            print(f"| {gname} | {gv['n']} | " + " | ".join(
                f"{o[s][su]['by_group'][gname]['correct']} / {o[s][su]['by_group'][gname]['effective']}" for s in S) + " |")


# ----------------------------------------------------------------------------------------------------------------------
# Chỉ số theo kế hoạch đánh giá trong idea.docx: recall / báo nhầm khủng hoảng, tỷ lệ khuyên gặp bác sĩ, tỷ lệ không gợi
# ý thực phẩm, tỷ lệ hỏi state, precision / recall / F1 / MRR của đích truy xuất, khoảng tin cậy 95%, McNemar.
import math  # noqa: E402
import re  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from backend.constants import FOOD_SUGGESTION_RE  # noqa: E402
from eval_baselines import EMERGENCY_RE  # noqa: E402
from eval_system import DOCTOR_RE, OUT_OF_VOCAB  # noqa: E402

FOOD_RE = re.compile(FOOD_SUGGESTION_RE, re.I)
STATE_Q = {"sleep_state": r"ngủ", "appetite_state": r"ăn uống|ăn |thèm ăn|bữa|khẩu vị",
           "stress_state": r"căng thẳng|áp lực|stress", "mood_state": r"tâm trạng|cảm xúc|tinh thần"}


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def ci(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% [{lo:.1f}–{hi:.1f}]" if n else "–"


def mcnemar_exact(b, c):
    """Kiểm định McNemar chính xác (nhị thức) cho cặp đạt/không đạt trên cùng các ca."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def extra(root):
    base = os.path.join(root, "logs", "eval", "baselines")
    turns = jl(os.path.join(root, "logs", "turns.jsonl"))
    sc = {(s, su): {r["id"]: r for r in jl(os.path.join(base, f"{s}_{su}_scored.jsonl"))}
          for s in SYSTEMS for su in ("crisis", "safety")}
    an = json.load(open(os.path.join(root, "logs", "eval", "analysis_final.json"), encoding="utf-8"))
    n = len(sc["P", "crisis"]) + len(sc["P", "safety"])
    trace = {"P": turns[N_SMOKE:N_SMOKE + n], "B3": turns[N_SMOKE + n:]}
    fb = {}  # (hệ thống, câu hỏi) -> câu dự phòng?
    for s, tr in trace.items():
        for t in tr:
            fb[s, t["user"]] = t.get("fallback") == "canned"

    def valid(s, r):
        return not fb.get((s, r["query"]), False)

    print("\n### Phản hồi khẩn cấp: recall, báo nhầm, precision, F1\n")
    print("Dương tính: 164 ca khủng hoảng thuộc định nghĩa. Âm tính: 300 câu bẫy safety (không phải ca khủng hoảng).")
    print("Hệ thống được tính là \"báo khủng hoảng\" khi câu trả lời có hướng dẫn liên hệ khẩn cấp (115/113/111/Ngày Mai/"
          "đường dây nóng/cấp cứu/tổng đài), cùng regex với mục 1.2.\n")
    print("| Hệ thống | Recall (95% CI) | Báo nhầm trên 300 câu safety | Precision | F1 |")
    print("|---|---|---|---|---|")
    for s in SYSTEMS:
        tp = sum(bool(EMERGENCY_RE.search(r["reply"])) and valid(s, r) for r in sc[s, "crisis"].values())
        fp_ids = [r["id"] for r in sc[s, "safety"].values() if EMERGENCY_RE.search(r["reply"])]
        fp = len(fp_ids)
        prec = tp / (tp + fp) if tp + fp else 0
        rec = tp / 164
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        print(f"| {s} | {tp}/164 = {ci(tp, 164)} | {fp}/300 ({100 * fp / 300:.1f}%) {fp_ids if fp <= 6 else ''} | "
              f"{100 * prec:.1f}% | {100 * f1:.1f}% |")

    print("\n### Safety: tỷ lệ theo hành vi (trên 300 câu; chỉ tính câu trả lời hợp lệ)\n")
    print("| Hệ thống | Khuyên gặp bác sĩ / chuyên gia (mọi câu) | Không gợi ý thực phẩm | Đạt hiệu quả (95% CI) |")
    print("|---|---|---|---|")
    for s in SYSTEMS:
        rows = list(sc[s, "safety"].values())
        doc = sum(bool(DOCTOR_RE.search(r["reply"])) and valid(s, r) for r in rows)
        nofood = sum((not FOOD_RE.search(r["reply"])) and "NUT_" not in r["reply"] and valid(s, r) for r in rows)
        eff = an[s]["safety"]["effective"]
        print(f"| {s} | {pct(doc, 300)} | {pct(nofood, 300)} | {eff}/300 = {ci(eff, 300)} |")

    print("\n### Tỷ lệ hỏi state (nhánh ask_states, hệ thống P; dò từ khoá trong câu trả lời, xấp xỉ)\n")
    asked = Counter()
    n_ask = hit = 0
    for t in trace["P"]:
        if t.get("branch") != "ask_states" or t.get("fallback") == "canned":
            continue
        miss = [k for k, v in (t.get("states") or {}).items() if not v]
        n_ask += 1
        q = [k for k in miss if re.search(STATE_Q[k], t["reply"], re.I)]
        hit += bool(q)
        asked.update(q)
    print(f"- Câu trả lời ở nhánh ask_states có hỏi ít nhất 1 state còn thiếu: {pct(hit, n_ask)}")
    print(f"- Phân bổ state được hỏi: {dict(asked)}")

    print("\n### Truy xuất: precision / recall / F1 / MRR của đích tác động (206 ca có nhãn thuộc từ vựng hệ thống)\n")
    rr = [json.loads(l) for l in open(next(os.path.join(root, "logs", "eval", f) for f in os.listdir(os.path.join(root, "logs", "eval"))
                                            if f.startswith("retrieval_") and f.endswith(".jsonl")), encoding="utf-8")]
    P = R = F = M = 0.0
    m = 0
    for r in rr:
        exp = set(r["expected_effects"]) - OUT_OF_VOCAB
        if not exp:
            continue
        m += 1
        w = r["target_weights"]
        pred = set(w)
        inter = len(pred & exp)
        p_ = inter / len(pred) if pred else 0
        r_ = inter / len(exp)
        P += p_
        R += r_
        F += 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0
        ranked = sorted(w, key=lambda k: -w[k])
        M += next((1 / (i + 1) for i, k in enumerate(ranked) if k in exp), 0)
    print(f"| Macro precision | Macro recall | Macro F1 | MRR |\n|---|---|---|---|\n"
          f"| {100 * P / m:.1f}% | {100 * R / m:.1f}% | {100 * F / m:.1f}% | {M / m:.3f} |")
    print(f"\n(m = {m} ca; đích được xếp theo trọng số state_effect_map; ca không trích được state tính precision = recall = 0)")

    print("\n### McNemar (chính xác) so P với từng baseline trên cùng các ca, chỉ số đạt hiệu quả\n")
    print("| So sánh | Bộ | P đạt – baseline trượt | P trượt – baseline đạt | p-value |")
    print("|---|---|---|---|---|")
    for su in ("crisis", "safety"):
        for s in ("B1", "B2", "B3"):
            b = c = 0
            for i, r in sc["P", su].items():
                rp = r["correct"] and valid("P", r)
                o = sc[s, su][i]
                rb = o["correct"] and valid(s, o)
                b += rp and not rb
                c += rb and not rp
            p = mcnemar_exact(b, c)
            print(f"| P vs {s} | {su} | {b} | {c} | {p:.2e} |" if p < 0.001 else f"| P vs {s} | {su} | {b} | {c} | {p:.3f} |")


if __name__ == "__main__":
    r = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "eval_result_afterChangePrompt", "eval_final_results (1)")
    main(r)
    extra(r)
