import json, re, sys, os, collections
D = sys.argv[1]
FIXED = ("Bạn là chuyên gia tư vấn tâm lý. Luôn phản hồi bằng sự thấu cảm.\nCHỈ gợi ý thực phẩm khi ROUTE_NUTRITION = true, "
         "và CHỈ dùng thực phẩm có trong [NUTRITION_CONTEXT], kèm mã nguồn. Nếu có MISSING_STATES, khéo léo hỏi thêm 1–2 thông tin còn thiếu. Trả về đúng JSON.")
OVR = ("[LỆNH ƯU TIÊN CAO NHẤT]:\nHệ thống phát hiện người dùng đang sử dụng thuốc điều trị y tế.\nNhiệm vụ của bạn:\n"
       "1. Thể hiện sự thấu cảm với tình trạng hiện tại của người dùng.\n"
       "2. TUYỆT ĐỐI KHÔNG gợi ý bất kỳ loại thực phẩm, thức uống hay dưỡng chất nào để tránh nguy cơ tương tác thuốc.\n"
       "3. Chuyển hướng an toàn: Khuyên người dùng báo cáo triệu chứng này với bác sĩ đang điều trị trực tiếp.")
STATES = ["sleep_state", "appetite_state", "stress_state", "mood_state"]
ORDER = ["ROUTE_NUTRITION", "MISSING_STATES", "SYSTEM_OVERRIDE", "CBT_CONTEXT", "NUTRITION_CONTEXT"]
FOOD = r"\b(ăn|uống|cháo|trà|nước ấm|sữa|cà phê|thực phẩm|món|bữa|rau|trái cây|hoa quả|thức uống|đồ uống|dưỡng chất|vitamin|canxi|magie|omega)\b"
XUNG = r"\b(chú|cô|bác|anh|chị|em|cháu|người mẹ|người bố)\b"
ACUTE = r"(tức ngực|khó thở|nghẹn thở|nôn|chóng mặt|mang thai|sụt cân)"
KHAM = r"(khám|bác sĩ|cơ sở y tế|bệnh viện|nhân viên y tế|chuyên gia y tế)"
MED = r"(thuốc|tiêm|liều|điều trị)"
CRISIS = r"(tự tử|tự sát|tự hại|rạch tay|muốn chết|không muốn sống|nhẹ nợ|đi cho xong|không muốn tỉnh dậy|kết thúc cuộc đời|chán sống)"
PROMISE = r"(buổi sau|hẹn gặp lại|tôi sẽ đưa bạn|lần gặp tới|buổi tới)"
MASS = r"(mg|kcal|g)\b"
REASON_BAN = r"(khủng hoảng|thân chủ|bệnh nhân|\bUser\b|\bAssistant\b|tư vấn viên|xác nhận|đã thu thập đủ|thiếu thông tin|missing states)"
KEYS = {"thought_process", "side_talk", "nutritional_advice", "source_reference"}
TPK = {"detected_emotions", "detected_symptoms", "trigger_nutrition", "reasoning"}

def grp(fn):
    m = re.search(r"B(\d)", fn)
    return "B%s" % m.group(1) if m else ("A" if "_A_" in fn else "?")

def parse_sys(s):
    if not s.startswith(FIXED): return None, "fixed_prompt_mismatch"
    rest = s[len(FIXED):]
    if not rest.startswith("\n\n"): return None, "no_blank_line_after_fixed"
    rest = rest[2:]
    keys = [m.group(1) for m in re.finditer(r"^\[([A-Z_]+)\]:", rest, re.M)]
    blocks = {}
    parts = re.split(r"^\[([A-Z_]+)\]:", rest, flags=re.M)
    for k, v in zip(parts[1::2], parts[2::2]):
        blocks[k] = v.strip()
    return (keys, blocks), None

user_msgs = collections.defaultdict(set)
sent_count = collections.Counter()
report = {}
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".jsonl"): continue
    g = grp(fn); split = "test" if fn.startswith("test") else "train"
    errs = collections.Counter(); ex = {}
    def E(k, i, note=""):
        errs[k] += 1
        ex.setdefault(k, []).append(f"L{i}{(': ' + note[:120]) if note else ''}") if len(ex.get(k, [])) < 3 else None
    n = 0; multi = 0
    for i, line in enumerate(open(os.path.join(D, fn), encoding="utf-8"), 1):
        if not line.strip(): E("empty_line", i); continue
        n += 1
        try: r = json.loads(line)
        except Exception as e: E("bad_json_line", i); continue
        if set(r) != {"messages"}: E("extra_keys(" + ",".join(sorted(set(r) - {"messages"})) + ")", i)
        ms = r.get("messages", [])
        roles = [m.get("role") for m in ms]
        if not roles or roles[0] != "system" or roles[-1] != "assistant": E("bad_role_order", i); continue
        if any(roles[j] == roles[j + 1] for j in range(len(roles) - 1)) or "system" in roles[1:]: E("bad_role_alternation", i)
        if len(ms) > 3: multi += 1
        for m in ms:
            if "  " in str(m.get("content")): E("double_space", i); break
        for m in ms[1:-1]:
            if m["role"] == "assistant" and str(m["content"]).lstrip().startswith("{"): E("history_assistant_is_json", i)
        last = ms[-1]["content"]
        users = [m["content"] for m in ms if m["role"] == "user"]
        user_msgs[(split)].add(users[-1].strip())
        if not isinstance(last, str): E("last_turn_not_string", i); continue
        try: o = json.loads(last)
        except Exception: E("last_turn_bad_json", i); continue
        if not isinstance(o, dict) or set(o) != KEYS: E("output_keys_wrong", i, str(list(o) if isinstance(o, dict) else o)); continue
        tp = o["thought_process"]
        if not isinstance(tp, dict): E("thought_process_not_object", i); continue
        if set(tp) != TPK: E("tp_keys_wrong", i, str(list(tp)))
        if not isinstance(o["source_reference"], list): E("source_reference_not_list", i)
        if not isinstance(tp.get("detected_symptoms"), list): E("symptoms_not_list", i)
        rs = tp.get("reasoning", "") or ""
        st = o.get("side_talk") or ""
        for s in re.split(r"(?<=[.!?])\s+", st):
            if len(s) > 25: sent_count[s] += 1
        if re.search(r"\b(\w+) \1\b", st + " " + (o.get("nutritional_advice") or "")): E("repeated_word", i, re.search(r"\b(\w+) \1\b", st + " " + (o.get("nutritional_advice") or "")).group(0))
        # system prompt
        p, perr = parse_sys(ms[0]["content"])
        if perr: E(perr, i, ms[0]["content"][:80]); continue
        keys, b = p
        if [k for k in ORDER if k in keys] != keys or any(k not in ORDER for k in keys): E("dynamic_block_order_or_unknown_key", i, str(keys))
        route = b.get("ROUTE_NUTRITION")
        if route not in ("true", "false"): E("route_bad_value", i, str(route)); continue
        route = route == "true"
        if tp.get("trigger_nutrition") is not route: E("trigger_ne_route", i)
        if not rs.startswith("ROUTE_NUTRITION = %s." % ("true" if route else "false")): E("reasoning_prefix_wrong", i, rs[:50])
        if re.search(REASON_BAN, rs, re.I): E("reasoning_banned_word(lvl3)", i, re.search(REASON_BAN, rs, re.I).group(0))
        ms_raw = b.get("MISSING_STATES")
        miss = None
        if ms_raw is not None:
            try: miss = json.loads(ms_raw.replace("'", '"'))
            except Exception: E("missing_states_unparsable", i, ms_raw)
            if isinstance(miss, list):
                if any(x not in STATES for x in miss): E("missing_states_invalid_name", i, ms_raw)
                elif miss != sorted(miss, key=STATES.index): E("missing_states_wrong_order", i, ms_raw)
                if miss == [] and not route: E("empty_missing_with_false", i)
        if "SYSTEM_OVERRIDE" in b and b["SYSTEM_OVERRIDE"] != OVR: E("override_text_mismatch", i, b["SYSTEM_OVERRIDE"][:60])
        for k in ("CBT_CONTEXT", "NUTRITION_CONTEXT"):
            if k not in b: E("missing_" + k, i)
        # per-group expectations
        exp = {"A": (False, "absent", False), "B1": (False, "nonempty", False), "B2": (True, "empty", False),
               "B3": (False, "absent", True), "B4": (False, "nonempty", False)}[g]
        if route != exp[0]: E("route_wrong_for_group", i)
        if exp[1] == "absent" and ms_raw is not None: E("missing_states_should_be_absent", i)
        if exp[1] == "nonempty" and not miss: E("missing_states_should_be_nonempty", i, str(ms_raw))
        if exp[1] == "empty" and miss != []: E("missing_states_should_be_[]", i, str(ms_raw))
        if exp[2] != ("SYSTEM_OVERRIDE" in b): E("override_presence_wrong", i)
        if g in ("A", "B3", "B4") and b.get("CBT_CONTEXT") != "None": E("cbt_should_be_None", i)
        if not route:
            if b.get("NUTRITION_CONTEXT") != "None": E("nutrition_ctx_should_be_None", i)
            if o["nutritional_advice"] is not None: E("advice_not_null_when_false", i)
            if o["source_reference"] != []: E("source_ref_not_empty_when_false", i)
            if re.search(FOOD, st, re.I): E("food_word_in_side_talk_when_false", i, re.search(FOOD, st, re.I).group(0))
        else:
            ctx = b.get("NUTRITION_CONTEXT", "")
            codes = set(re.findall(r"NUT_\w+", ctx))
            if not codes: E("route_true_no_nut_codes", i)
            if re.search(r"NUT_x|placeholder", ctx, re.I): E("placeholder_code", i)
            if not o["nutritional_advice"]: E("advice_empty_when_true", i)
            if not o["source_reference"]: E("source_ref_empty_when_true", i)
            if any(c not in codes for c in o["source_reference"]): E("source_ref_not_in_context", i, str(o["source_reference"]))
            if re.search(r"\d\s*" + MASS, o["nutritional_advice"] or ""): E("mg_g_kcal_in_advice", i)
        if re.search(XUNG, st + " " + (o["nutritional_advice"] or ""), re.I): E("age_gender_address(lvl2)", i, re.search(XUNG, st, re.I).group(0) if re.search(XUNG, st, re.I) else "")
        if re.search(PROMISE, st, re.I): E("promise_beyond_bot(lvl2)", i, re.search(PROMISE, st, re.I).group(0))
        alluser = " ".join(users)
        if re.search(ACUTE, alluser, re.I) and not re.search(KHAM, st, re.I): E("acute_symptom_no_doctor_advice(lvl2)", i, re.search(ACUTE, alluser, re.I).group(0))
        if g in ("B1", "B2", "B4") and re.search(MED, alluser, re.I): E("medication_mention_outside_B3(lvl2)", i, re.search(MED, alluser, re.I).group(0))
        if g in ("B1", "B2", "B4", "A") and re.search(CRISIS, alluser, re.I): E("crisis_signal(lvl2)", i, re.search(CRISIS, alluser, re.I).group(0))
        if g == "B3" and not re.search(r"bác sĩ", st): E("B3_no_doctor_redirect", i)
    report[fn] = (n, multi, errs, ex)

for fn, (n, multi, errs, ex) in report.items():
    print(f"\n=== {fn}: {n} mẫu, {multi} nhiều lượt ({100*multi/max(n,1):.0f}%)")
    for k, v in errs.most_common():
        print(f"  {k}: {v}   {ex.get(k, [])}")
tr, te = user_msgs["train"], user_msgs["test"]
print("\nLeak: last-user msg identical train∩test:", len(tr & te))
for s in list(tr & te)[:5]: print("   ", s[:100])
rep = [(s, c) for s, c in sent_count.items() if c > 5]
print("Câu side_talk lặp >5 lần:", len(rep))
for s, c in sorted(rep, key=lambda x: -x[1])[:15]: print(f"  {c}x {s[:110]}")
