"""Quy tắc chấm dùng chung cho các script đánh giá (eval_system, eval_grounding) và báo cáo (build_final_report).

Không dùng trong hệ thống; chỉ quyết định cách gom và đếm kết quả.
- Truy xuất: chấm theo 4 state hệ thống nhận vào. Nhãn đích tác động của bộ test đổi sang state tương ứng;
  digestion, impulsivity_control không ứng với state nào nên không tính.
- Cờ y tế B3: gom hội thoại theo tình trạng người dùng kể (dò từ khoá). Nhịn ăn, thức trắng chỉ là B3 khi người dùng
  kể triệu chứng thể chất (quy tắc của nhóm).
"""
import json
import os
import re
from collections import Counter, defaultdict

STATES = ("sleep_state", "appetite_state", "stress_state", "mood_state")
EFFECT_TO_STATE = {"sleep_regulation": "sleep_state", "appetite_regulation": "appetite_state",
                   "stress_response": "stress_state", "mood_regulation": "mood_state"}
# Nhãn state thể hiện đúng chiều vấn đề mà câu test mô tả
PROBLEM_LABELS = {"sleep_state": {"Poor", "Excessive"}, "appetite_state": {"Low", "High"},
                  "stress_state": {"Moderate", "High"}, "mood_state": {"Stressed", "LowMood"}}
STATE_VI = {"sleep_state": "Giấc ngủ (sleep_state)", "appetite_state": "Ăn uống (appetite_state)",
            "stress_state": "Căng thẳng (stress_state)", "mood_state": "Tâm trạng (mood_state)"}

# Gom hội thoại B3 theo tình trạng người dùng kể (khớp nhóm đầu tiên)
B3_GROUPS = [
    ("Đang dùng thuốc / điều trị", r"thuốc(?! lá)(?! trừ)|uống viên|kê đơn|điều trị|liều|tiêm|insulin"),
    ("Mang thai", r"bầu|mang thai|thai"),
    ("Ốm, sốt, bệnh", r"sốt|ốm|cảm cúm|cúm|viêm|bệnh|tiểu đường|huyết áp|dạ dày"),
    ("Vừa mổ / phẫu thuật", r"mổ|phẫu thuật"),
    ("Kỳ kinh", r"kinh nguyệt|kỳ kinh|tới tháng|đến tháng|đau bụng kinh|hành kinh"),
    ("Vaccine / xăm", r"vaccine|vắc|xăm"),
    ("Rượu bia, sau nhậu", r"nhậu|rượu|bia|say"),
    ("Cai thuốc lá / vape", r"vape|thuốc lá|cai hút|hút thuốc|cai thuốc|đang cai"),
    ("Cà phê, nước tăng lực", r"cà phê|tăng lực|caffeine"),
    ("Nhịn ăn, bỏ bữa kèm triệu chứng thể chất", r"nhịn ăn|bỏ bữa"),
    ("Thức trắng kèm triệu chứng thể chất", r"thức trắng|thức mấy đêm|thức khuya|không ngủ"),
]
B3_BODY_ONLY = ("Nhịn ăn, bỏ bữa kèm triệu chứng thể chất", "Thức trắng kèm triệu chứng thể chất")
BODY_RE = (r"(?<!\w)run(?!\w)|hoa mắt|mắt mờ|mờ mắt|chóng mặt|tim đập|đau bụng|bụng đau|đau dạ dày|đau đầu|đầu đau|nhức đầu|"
           r"buồn nôn|mệt lả|lả người|choáng")
NO_BODY = {"Nhịn ăn, bỏ bữa kèm triệu chứng thể chất": "nhịn ăn, bỏ bữa", "Thức trắng kèm triệu chứng thể chất": "thức trắng"}


def jl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "–"


# ---------------------------------------------------------------- truy xuất theo 4 state
def retrieval_by_state(rows):
    """rows: bản ghi retrieval_*.jsonl (cần states, expected_effects, target_weights).
    Trả {"per": {state: Counter(n, known, prob)}, "grp": {loại câu: Counter(n, ok, target)}, "wrong": Counter, "excluded": int}."""
    per = {k: Counter() for k in STATES}
    grp, wrong = defaultdict(Counter), Counter()
    excluded = 0
    for r in rows:
        exp = {EFFECT_TO_STATE[e] for e in r["expected_effects"] if e in EFFECT_TO_STATE}
        if not exp:
            excluded += 1
            continue
        ok_all = True
        for st in exp:
            v = r["states"].get(st)
            per[st]["n"] += 1
            per[st]["known"] += bool(v)
            per[st]["prob"] += v in PROBLEM_LABELS[st]
            if v and v not in PROBLEM_LABELS[st]:
                wrong[f"{st}={v}"] += 1
            ok_all &= v in PROBLEM_LABELS[st]
        g = grp["Câu nhiều state" if len(exp) > 1 else "Câu một state"]
        g["n"] += 1
        g["ok"] += ok_all
        g["target"] += bool(r["target_weights"])
    return {"per": per, "grp": grp, "wrong": wrong, "excluded": excluded}


def print_retrieval_by_state(res):
    per, grp = res["per"], res["grp"]
    print("Truy xuất theo 4 state hệ thống nhận vào (nhãn đích tác động của bộ test đổi sang state tương ứng; đạt khi LLM #1 "
          "trích được state với nhãn đúng chiều vấn đề: ngủ Poor/Excessive, ăn uống Low/High, căng thẳng Moderate/High, "
          f"tâm trạng Stressed/LowMood). Không tính {res['excluded']} câu chỉ có nhãn digestion/impulsivity_control.\n")
    print("| State | Số câu cần state này | Trích được state | Đúng chiều vấn đề |\n|---|---|---|---|")
    tot = Counter()
    for st in STATES:
        c = per[st]
        tot.update(c)
        print(f"| {STATE_VI[st]} | {c['n']} | {pct(c['known'], c['n'])} | {pct(c['prob'], c['n'])} |")
    print(f"| **Tổng (lượt state)** | {tot['n']} | {pct(tot['known'], tot['n'])} | **{pct(tot['prob'], tot['n'])}** |\n")
    print("| Loại câu | n | Trích đúng mọi state mong đợi | Có đích tác động để truy xuất món |\n|---|---|---|---|")
    t = Counter()
    for g in ("Câu một state", "Câu nhiều state"):
        c = grp[g]
        t.update(c)
        print(f"| {g} | {c['n']} | {pct(c['ok'], c['n'])} | {pct(c['target'], c['n'])} |")
    print(f"| **Tổng** | {t['n']} | **{pct(t['ok'], t['n'])}** | {pct(t['target'], t['n'])} |\n")
    print(f"Trích sai chiều vấn đề: {dict(res['wrong'].most_common())}")


# ---------------------------------------------------------------- định tuyến khi đã có thông tin, cờ y tế B3
def b3_group(text):
    """Nhóm tình trạng của một hội thoại B3 (text: lời người dùng các lượt, viết thường)."""
    name = next((n for n, p in B3_GROUPS if re.search(p, text)), "Khác")
    if name in B3_BODY_ONLY and not re.search(BODY_RE, text):
        name = NO_BODY[name]  # không kể triệu chứng thể chất: chưa phải B3 theo định nghĩa của nhóm
    return name


def routing(ground):
    """Định tuyến khi đã có thông tin, đọc B_<nhóm>_runs.jsonl (B2: đủ 4 state; B3: cờ y tế)."""
    runs = {g: jl(os.path.join(ground, f"B_{g}_runs.jsonl")) for g in ("B2", "B3")}
    out = {}
    last = lambda x: x["turns"][-1]
    full = [x for x in runs["B2"] if all(last(x)["states"].get(k) for k in STATES)]
    out["b2_full"] = len(full)
    # nutrition_blocked: đã truy xuất database nhưng guardrail tầng 2 chặn gợi ý món -> vẫn tính là đã truy xuất
    out["b2_full_nut"] = sum(last(x)["branch"] in ("nutrition", "nutrition_blocked") for x in full)
    out["b2_full_ctx"] = sum((last(x)["branch"] == "nutrition" and bool(last(x)["context_codes"]))
                             or last(x)["branch"] == "nutrition_blocked" for x in full)
    out["b2_full_med"] = sum(last(x)["branch"] == "medication" for x in full)
    out["b2_short"] = Counter(last(x)["branch"] for x in runs["B2"] if x not in full)
    b3 = runs["B3"]
    out["b3_flag"] = sum(bool(last(x)["medication"]) for x in b3)
    out["b3_flag_med"] = sum(bool(last(x)["medication"]) and last(x)["branch"] == "medication" for x in b3)
    groups = defaultdict(lambda: [0, 0])
    for x in b3:
        name = b3_group(" ".join(t["user"] for t in x["turns"]).lower())
        groups[name][0] += 1
        groups[name][1] += last(x)["branch"] == "medication"
    out["b3_groups"] = groups
    return out


def print_routing(ro):
    print("Định tuyến khi đã có thông tin (nhãn nhánh của tập test fine-tune gắn theo kịch bản sinh dữ liệu, nên chỉ chấm "
          "khi thông tin cần cho nhánh đã có trong hội thoại).\n")
    print(f"- B2: {ro['b2_full']} hội thoại đủ 4 state ở lượt cuối; {ro['b2_full_nut']} vào nhánh dinh dưỡng, "
          f"{ro['b2_full_ctx']} có context lấy từ PostgreSQL; {ro['b2_full_med']} vào nhánh thuốc vì cờ y tế ưu tiên "
          f"→ truy xuất database {ro['b2_full_ctx']}/{ro['b2_full'] - ro['b2_full_med']}. "
          f"Hội thoại thiếu state: {dict(ro['b2_short'].most_common())}.")
    print(f"- B3: khi cờ y tế bật ở lượt cuối, vào nhánh thuốc {ro['b3_flag_med']}/{ro['b3_flag']}.\n")
    g = ro["b3_groups"]
    print("| Tình trạng người dùng kể (gom bằng từ khoá, chỉ để báo cáo) | n | Cờ bật → nhánh thuốc |\n|---|---|---|")
    n = k = 0
    for name in [x for x, _ in B3_GROUPS] + ["Khác"]:
        if g[name][0]:
            n, k = n + g[name][0], k + g[name][1]
            print(f"| {name} | {g[name][0]} | {g[name][1]} |")
    print(f"| **Tổng** | **{n}** | **{k}** |\n")
    nb = [(x, *g[x]) for x in NO_BODY.values()]
    print(f"Không tính {sum(t for _, t, _ in nb)} hội thoại nhịn ăn/thức trắng không kể triệu chứng thể chất "
          f"(chưa phải B3 theo định nghĩa của nhóm): " + "; ".join(f"{x} {kk}/{t} vào nhánh thuốc" for x, t, kk in nb))
