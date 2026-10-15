"""Sửa dữ liệu traindata theo idea.docx. Chạy: python -I -X utf8 fix.py <traindata_dir> <nutrition_db.json>"""
import json, re, sys, os, hashlib

D, DB = sys.argv[1], sys.argv[2]
FILES = [f for f in sorted(os.listdir(D)) if f.endswith(".jsonl") and not f.startswith("safety")]
STATES = ["sleep_state", "appetite_state", "stress_state", "mood_state"]
db = json.load(open(DB, encoding="utf-8"))
LOG, REMOVED = [], []
data = {fn: [json.loads(l) for l in open(os.path.join(D, fn), encoding="utf-8")] for fn in FILES}


def log(fn, i, action, field, before, after):
    LOG.append({"file": fn, "line": i, "action": action, "field": field, "before": before, "after": after})


def sents(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def pick(seq, key):
    return seq[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(seq)]


def dumps(o):
    return json.dumps(o, ensure_ascii=False)


# ---------- danh sách sửa thủ công đã rà ----------
REMOVE = {  # (file, line): lý do -> tách khỏi tập, lưu vào removed_samples.jsonl
    ("group_A_formatted.jsonl", 600): "dùng thuốc (mồi B3), nhắc tự tử",
    ("group_A_formatted.jsonl", 1665): "đang dùng thuốc điều trị (mồi B3)",
    ("group_A_formatted.jsonl", 121): "câu trả lời có nhận định y khoa sai (nhịn ăn, thải độc thận) và lạc đề",
    ("test_A_formatted.jsonl", 697): "đang dùng thuốc (mồi B3-test)",
    ("group_B_B1.jsonl", 341): "tín hiệu khủng hoảng 'muốn chết đi cho xong' -> phản hồi soạn sẵn, không thuộc B1",
    ("group_B_B1.jsonl", 558): "tín hiệu khủng hoảng 'muốn chết đi cho xong'; side_talk gợi ý nước đường/đồ ăn khi ROUTE false",
    ("group_B_B1.jsonl", 602): "tín hiệu khủng hoảng 'muốn tự tử'",
    ("group_B_B1.jsonl", 657): "tín hiệu khủng hoảng 'muốn chết đi cho xong'",
    ("group_B_B1.jsonl", 208): "ý định tự sát rõ 'muốn kết thúc cuộc sống này' -> phản hồi soạn sẵn",
    ("group_B_B1.jsonl", 362): "tín hiệu khủng hoảng 'muốn biến mất khỏi thế giới này'; side_talk không xử lý rủi ro",
    ("test_B_B1.jsonl", 51): "đang uống thuốc hạ áp (thuộc B3)",
    ("test_B_B1.jsonl", 109): "dùng thuốc an thần (thuộc B3)",
}
PROMISE_DEL = {  # câu hứa hẹn ngoài khả năng chatbot: xóa nguyên câu
    "group_A_formatted.jsonl": [363, 1179, 1349, 1384, 1743, 1797, 1800, 1841, 1856, 1974, 2467, 2525, 2892, 3440, 3685],
    "test_A_formatted.jsonl": [79, 94, 441, 491, 935],
}
PROMISE_RE = r"buổi sau|buổi tới|hẹn gặp lại|buổi tiếp nhận"
REPEAT_FIX = [  # (file, line, sai, đúng) — từ lặp thật, không phải từ láy
    ("group_A_formatted.jsonl", 1291, "của bạn bạn", "của bạn"), ("group_A_formatted.jsonl", 2544, "của bạn bạn", "của bạn"),
    ("group_A_formatted.jsonl", 1228, "của bạn bạn", "của bạn"), ("group_A_formatted.jsonl", 3129, "của bạn bạn", "của bạn"),
    ("group_A_formatted.jsonl", 2162, "của bạn bạn", "của bạn"), ("group_A_formatted.jsonl", 3441, "bước bước", "bước"),
    ("group_A_formatted.jsonl", 2007, "bước bước", "bước"), ("group_A_formatted.jsonl", 2929, "bước bước", "bước"),
    ("group_A_formatted.jsonl", 1833, "từ bước bước vào", "từ lúc bước vào"), ("group_A_formatted.jsonl", 1861, "hay hay", "hay"),
    ("group_A_formatted.jsonl", 1733, "ra ra sao", "ra sao"), ("group_A_formatted.jsonl", 800, "mong muốn muốn", "mong muốn"),
    ("group_B_B1.jsonl", 675, "hay hay", "hay"), ("group_B_B1.jsonl", 678, "hay hay", "hay"), ("group_B_B1.jsonl", 809, "hay hay", "hay"),
    ("group_B_B1.jsonl", 907, "ra ra sao", "ra sao"), ("group_B_B1.jsonl", 890, "ra ra sao", "ra sao"), ("group_B_B1.jsonl", 911, "ra ra sao", "ra sao"),
]
MISSING_SET = {("test_B_B1.jsonl", 27): ["appetite_state"], ("test_B_B1.jsonl", 63): ["appetite_state"]}

# ---------- câu hỏi state cho B1 ----------
QUESTIONS = {
    "sleep_state": ["Mấy hôm nay giấc ngủ của bạn thế nào?", "Dạo này bạn ngủ có ngon giấc không?",
                    "Những đêm gần đây bạn ngủ ra sao?", "Chuyện ngủ nghỉ của bạn mấy hôm nay thế nào?",
                    "Gần đây bạn có ngủ đủ giấc không?", "Đêm đến bạn thường ngủ thế nào?"],
    "appetite_state": ["Dạo này chuyện ăn uống của bạn thế nào?", "Mấy hôm nay bạn ăn uống ra sao?",
                       "Gần đây bạn ăn có thấy ngon miệng không?", "Mấy ngày qua bạn ăn uống có đều không?",
                       "Chuyện ăn uống của bạn dạo này có gì thay đổi không?", "Dạo gần đây khẩu vị của bạn thế nào?"],
    "stress_state": ["Ngoài chuyện này, dạo gần đây bạn có thấy căng thẳng nhiều không?",
                     "Mấy hôm nay mức độ áp lực của bạn thế nào?", "Gần đây còn điều gì khác khiến bạn thấy áp lực không?",
                     "Bạn thấy mình căng thẳng nhiều nhất vì chuyện gì?"],
    "mood_state": ["Tâm trạng của bạn mấy hôm nay thế nào?", "Nhìn chung dạo này bạn thấy tinh thần mình ra sao?",
                   "Những ngày gần đây tâm trạng bạn thế nào?", "Bạn thấy cảm xúc của mình mấy hôm nay ra sao?"],
}
LEADS = ["", "", "", "Cho mình hỏi thêm một chút, ", "Nếu bạn thấy thoải mái thì kể mình nghe nhé, ",
         "Mình muốn hiểu thêm về bạn một chút, ", "Bên cạnh đó, ", "Mình cũng muốn hỏi thăm, "]
STATE_KW = [("appetite_state", r"ăn uống|bữa ăn|bữa|ăn|khẩu vị"), ("sleep_state", r"giấc ngủ|ngủ|giấc"),
            ("mood_state", r"tâm trạng|tinh thần|cảm xúc"), ("stress_state", r"căng thẳng|áp lực|stress")]
WISH = r"^(Mong|Hy vọng|Hi vọng|Chúc|Mình mong|Mình chỉ mong|Mình hy vọng|Mình thực sự hy vọng|Dù chuyện gì|Những lúc thế này|Tối nay hãy)|\b(mong là|mong rằng|hy vọng|hi vọng|mình chỉ mong)\b"
KEEP = r"khám|bác sĩ|cơ sở y tế|cấp cứu|chuyên gia|nhân viên y tế|đường dây"

# ---------- lời khuyên đi khám khi có triệu chứng cơ thể rõ rệt ----------
SYMPTOMS = [("nôn nhiều", r"nôn (thốc|khan|ói|ra|mửa)|nôn thốc|(ăn|nuốt)[^.,]{0,12}(là |cũng )?(chực )?nôn"),
            ("khó thở", r"khó thở|hít thở rất nông|nghẹt thở"), ("tức ngực", r"tức ngực|ngực[^.,]{0,12}(nằng nặng|căng tức|đau tức|tức anh ách|tức nghẹn)"),
            ("chóng mặt", r"chóng mặt|hoa mắt|xây xẩm|váng đầu|suýt ngã|suýt ngất"), ("huyết áp tăng", r"huyết áp (tăng|cao)"),
            ("sụt cân", r"(đã|bị) sụt cân|sụt cân ngoài ý muốn")]
SYM_EXCL = r"tăng chóng mặt|một cách chóng mặt|nghĩ đến thôi tôi đã thấy chóng mặt|xoay vòng|khách say|nôn ra xe|chưa sụt cân|không sụt cân|con trai tôi hay nôn|anh ấy bắt đầu|phụ nữ mang thai|sợ (bị )?nôn"
KHAM_RE = r"khám|bác sĩ|cơ sở y tế|bệnh viện|nhân viên y tế|y tế|cấp cứu"
ADVICE = ["Những biểu hiện như {s} nên được bác sĩ kiểm tra, và nếu thấy nặng lên, bạn hãy đến cơ sở y tế ngay nhé.",
          "Nếu tình trạng {s} còn tiếp diễn, bạn nên đi khám để được kiểm tra, và đến cơ sở y tế ngay nếu thấy nặng hơn.",
          "Với tình trạng {s} như vậy, bạn nên đi khám sớm để yên tâm hơn, và đến cơ sở y tế ngay nếu thấy nặng lên.",
          "Tình trạng {s} là điều bạn nên đi khám để bác sĩ kiểm tra, nhất là nếu nó kéo dài hoặc nặng hơn."]


def symptoms_of(text):
    if re.search(SYM_EXCL, text): text = re.sub(r"[^.!?]*(" + SYM_EXCL + r")[^.!?]*", "", text)
    return [n for n, rx in SYMPTOMS if re.search(rx, text)]


# ---------- xưng "em" -> "bạn" ----------
EM_KEEP = r"(em bé|em gái|em trai|em út|em nhỏ|em ấy|em họ|em ruột|em dâu|em rể|anh em|chị em|các em|trẻ em|cho em bé|con em|em của bạn|em mình)"
EM_ADDR = r"(cảm ơn em|em nên|em đang|em đã|em cứ|em hãy|em vẫn|em thấy|em cảm|em có|em không|em sẽ|em vừa|của em|cho em|với em|hiểu em|như em|em lo|em muốn|em thử|em mất|em dám|em nhớ|em buồn)"


def em_to_ban(t):
    if not re.search(r"\b[Ee]m\b", t):
        return t
    marks = {}
    def protect(m):
        k = "\u0001%d\u0001" % len(marks); marks[k] = m.group(0); return k
    t2 = re.sub(EM_KEEP, protect, t, flags=re.I)
    t2 = re.sub(r"\bEm\b", "Bạn", t2)
    t2 = re.sub(r"\bem\b", "bạn", t2)
    for k, v in marks.items():
        t2 = t2.replace(k, v)
    return t2


def addresses_user_as_em(r):
    assist = [m["content"] for m in r["messages"][1:-1] if m["role"] == "assistant"]
    o = json.loads(r["messages"][-1]["content"])
    txt = " ".join(assist + [o["side_talk"]])
    users = " ".join(m["content"] for m in r["messages"] if m["role"] == "user")
    hits = len(re.findall(EM_ADDR, re.sub(EM_KEEP, "", txt, flags=re.I), re.I))
    return hits >= 1


# ================= áp dụng =================
out = {}
for fn in FILES:
    grp = "A" if "_A_" in fn else re.search(r"B\d", fn).group(0)
    kept = []
    for i, r in enumerate(data[fn], 1):
        if (fn, i) in REMOVE:
            REMOVED.append({"file": fn, "line": i, "reason": REMOVE[(fn, i)], "record": r})
            log(fn, i, "remove_sample", "", REMOVE[(fn, i)], ""); continue
        ms = r["messages"]
        o = json.loads(ms[-1]["content"])
        tp = o["thought_process"]
        sysc = ms[0]["content"]

        # 1. khoảng trắng kép
        for j, m in enumerate(ms[:-1]):
            new = re.sub(r" {2,}", " ", m["content"])
            if new != m["content"]: log(fn, i, "double_space", f"messages[{j}]", m["content"], new); m["content"] = new
        for k in ("side_talk", "nutritional_advice"):
            if isinstance(o.get(k), str):
                new = re.sub(r" {2,}", " ", o[k])
                if new != o[k]: log(fn, i, "double_space", k, o[k], new); o[k] = new
        new = re.sub(r" {2,}", " ", tp["reasoning"])
        if new != tp["reasoning"]: log(fn, i, "double_space", "reasoning", tp["reasoning"], new); tp["reasoning"] = new

        # 2. viết hoa chữ cái đầu detected_emotions
        e = tp["detected_emotions"]
        if e and e[0].islower():
            tp["detected_emotions"] = e[0].upper() + e[1:]

        # 3. MISSING_STATES: thứ tự chuẩn / gán lại
        m = re.search(r"\[MISSING_STATES\]: (.*)", sysc)
        if m:
            cur = json.loads(m.group(1))
            want = MISSING_SET.get((fn, i), sorted(cur, key=STATES.index))
            if want != cur:
                sysc = sysc.replace(m.group(0), "[MISSING_STATES]: " + dumps(want))
                log(fn, i, "missing_states", "system", cur, want)

        # 4. B2: tên thực phẩm theo DB + viết lại reasoning
        if grp == "B2":
            def norm(mm):
                n = int(mm.group(1)); name = db[n - 1]["food_item"]
                if mm.group(2) != name: log(fn, i, "nut_name", "system", mm.group(2), name)
                return f"NUT_{mm.group(1)} – {name} |"
            sysc = re.sub(r"NUT_(\d+) – (.*?) \|", norm, sysc)
            rs0 = tp["reasoning"]
            rs = rs0.replace(" Xác nhận đã đủ thông tin (không còn missing states).", "")
            rs = rs.replace("Trợ lý thể hiện sự thấu cảm chân thành", "Phản hồi thể hiện sự thấu cảm")
            if "Thân chủ" in rs:  # test B2: thay câu dán nguyên tin nhắn bằng mô tả từ thought_process
                head, tail = rs.split(" Phản hồi thể hiện", 1)
                emo = tp["detected_emotions"].lower()
                sym = tp["detected_symptoms"]
                desc = f"Người dùng đang trong trạng thái {emo}" + (f", kèm biểu hiện {', '.join(sym)}." if sym else ".")
                rs = "ROUTE_NUTRITION = true. " + desc + " Phản hồi thể hiện" + tail
            cbt = re.search(r"\[CBT_CONTEXT\]: (.*)", sysc).group(1)
            mm = re.search(r"kết hợp bài tập (.*?) từ context, ", rs)
            if mm:
                if cbt == "None":
                    rs = rs.replace(mm.group(0), "")
                else:
                    cname = re.sub(r"\s*\(.*?\)", "", cbt.split(" – ", 1)[1].split(" | ")[0]).strip()
                    if mm.group(1).lower() != cname.lower():
                        rs = rs.replace(mm.group(0), f"kết hợp bài tập {cname} từ context, ")
            if rs != rs0: log(fn, i, "b2_reasoning", "reasoning", rs0, rs); tp["reasoning"] = rs
            st0 = o["side_talk"]
            dup = "Bạn cứ cho phép cơ thể và tâm trí được nghỉ ngơi, buông lỏng tự nhiên nhé."
            if dup in st0 and len(sents(st0)) >= 3:
                o["side_talk"] = re.sub(r"\s*" + re.escape(dup), "", st0).strip()
                log(fn, i, "delete_sentence(lvl3_template)", "side_talk", dup, "")

        # 5. B1: bảo đảm hỏi 1 state trong MISSING_STATES
        if grp == "B1":
            miss = json.loads(re.search(r"\[MISSING_STATES\]: (.*)", sysc).group(1))
            st0 = o["side_talk"]
            if "?" not in st0 and miss:
                ss = sents(st0)
                removed = []
                while len(ss) > 1 and re.search(WISH, ss[-1]) and not re.search(KEEP, ss[-1]):
                    removed.insert(0, ss.pop())
                rs = tp["reasoning"]
                WISHV = r"hỏi|nhắc nhở|nhắc|chúc|dặn dò|giữ gìn|duy trì|mong|lời động viên|kết nối tới|hướng tới|khai thác|gợi mở|khơi gợi|chuyển ý|thiếu thông tin|động viên"
                mv = list(re.finditer(WISHV, rs))
                tail = rs[mv[0].start():] if mv else ""
                target = None
                for stt, kw in STATE_KW:
                    if stt in miss and re.search(kw, tail):
                        target = stt; break
                if target is None:
                    for stt, kw in STATE_KW:
                        if stt in miss and any(re.search(kw, s) for s in removed):
                            target = stt; break
                target = target or miss[0]
                core = pick(QUESTIONS[target], fn + str(i))
                lead = pick(LEADS, "lead" + fn + str(i))
                q = lead + (core[0].lower() + core[1:] if lead else core)
                o["side_talk"] = " ".join(ss + [q])
                log(fn, i, "b1_add_state_question", "side_talk", " ".join(removed), q)
                qname = {"sleep_state": "giấc ngủ", "appetite_state": "chuyện ăn uống", "stress_state": "mức độ căng thẳng", "mood_state": "tâm trạng"}[target]
                # thay mệnh đề cuối mô tả lời chúc/nhắc nhở bằng "hỏi thăm về <state>"
                body = rs.rstrip(" .")
                ss_r = sents(body)
                lastS = ss_r[-1]; pre = " ".join(ss_r[:-1])
                rs1 = None
                if len(ss_r) > 1 and re.match(r"(Sau đó,?|Cuối cùng,?|Rồi) ", lastS) and re.search(WISHV, lastS):
                    rs1 = pre + " Sau đó hỏi thăm về " + qname + "."
                else:
                    cuts = [m.start() for m in re.finditer(r"(; |, | )(sau đó,? |rồi |và |đồng thời |cuối cùng )|; |, | và ", lastS)]
                    for c in reversed(cuts):
                        if re.search(WISHV, lastS[c:]):
                            rs1 = (pre + " " if pre else "") + lastS[:c] + ", sau đó hỏi thăm về " + qname + "."
                            break
                if rs1 is None:
                    rs1 = body + ", rồi hỏi thăm về " + qname + "."
                if rs1 != rs: log(fn, i, "b1_reasoning", "reasoning", rs, rs1); tp["reasoning"] = rs1

        # 6. xưng "em" với người dùng -> "bạn" (lời chatbot, nhóm B)
        if grp != "A" and addresses_user_as_em(r):
            for j, mm in enumerate(ms[1:-1], 1):
                if mm["role"] == "assistant":
                    new = em_to_ban(mm["content"])
                    if new != mm["content"]: log(fn, i, "em_to_ban", f"messages[{j}]", mm["content"], new); mm["content"] = new
            for k in ("side_talk",):
                new = em_to_ban(o[k])
                if new != o[k]: log(fn, i, "em_to_ban", k, o[k], new); o[k] = new
            new = em_to_ban(tp["reasoning"])
            if new != tp["reasoning"]: log(fn, i, "em_to_ban", "reasoning", tp["reasoning"], new); tp["reasoning"] = new

        # 6b. lời khuyên đi khám (mọi nhóm trừ B3 vốn đã chuyển cho bác sĩ)
        if grp != "B3":
            utext = " ".join(m["content"] for m in ms if m["role"] == "user")
            syms = symptoms_of(utext)
            if syms and not re.search(KHAM_RE, o["side_talk"]):
                s = " và ".join(syms[:2])
                adv = pick(ADVICE, "adv" + fn + str(i)).format(s=s)
                ss = sents(o["side_talk"])
                if ss and ss[-1].endswith("?"): ss.insert(len(ss) - 1, adv)
                else: ss.append(adv)
                o["side_talk"] = " ".join(ss)
                log(fn, i, "add_sentence(see_doctor)", "side_talk", "", adv)
                rs0 = tp["reasoning"]
                tp["reasoning"] = rs0.rstrip() + f" Phản hồi khuyên người dùng đi khám vì {s}."
                log(fn, i, "add_sentence(see_doctor)", "reasoning", "", f"Phản hồi khuyên người dùng đi khám vì {s}.")

        # 7. câu hứa hẹn
        if i in PROMISE_DEL.get(fn, []):
            ss = sents(o["side_talk"]); keep = [s for s in ss if not re.search(PROMISE_RE, s, re.I)]
            for s in ss:
                if s not in keep: log(fn, i, "delete_sentence(promise)", "side_talk", s, "")
            o["side_talk"] = " ".join(keep)

        # 8. từ lặp
        for f2, l2, a, b in REPEAT_FIX:
            if f2 == fn and l2 == i:
                for k in ("side_talk", "nutritional_advice"):
                    if isinstance(o.get(k), str) and a in o[k]: o[k] = o[k].replace(a, b, 1); log(fn, i, "repeated_word", k, a, b)
                if a in tp["reasoning"]: tp["reasoning"] = tp["reasoning"].replace(a, b, 1); log(fn, i, "repeated_word", "reasoning", a, b)

        ms[0]["content"] = sysc
        ms[-1]["content"] = dumps(o)
        kept.append(r)
    out[fn] = kept

for fn, recs in out.items():
    with open(os.path.join(D, fn), "w", encoding="utf-8", newline="\n") as f:
        for r in recs: f.write(dumps(r) + "\n")
logdir = os.path.join(os.path.dirname(os.path.abspath(D)), "traindata_logs")
os.makedirs(logdir, exist_ok=True)
with open(os.path.join(logdir, "change_log.jsonl"), "w", encoding="utf-8") as f:
    for x in LOG: f.write(dumps(x) + "\n")
with open(os.path.join(logdir, "removed_samples.jsonl"), "w", encoding="utf-8") as f:
    for x in REMOVED: f.write(dumps(x) + "\n")
import collections
print(collections.Counter(x["action"] for x in LOG))
print({fn: len(v) for fn, v in out.items()})
