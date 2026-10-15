"""Bước 2: (1) bỏ mẫu B2-train trùng hoàn toàn chuỗi tin nhắn user với B2-test;
(2) chuyển mẫu khủng hoảng / dùng thuốc đã tách ở bước 1 sang safetyguard.jsonl.
Chạy: python -I -X utf8 traindata_logs/finalize_step2.py  (từ thư mục C:/FPT/AIM)"""
import json

T, LOGD = "traindata", "traindata_logs"


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def save(p, rows):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")


def users(r):
    return tuple(m["content"].strip() for m in r["messages"] if m["role"] == "user")


changes, removed = load(f"{LOGD}/change_log.jsonl"), load(f"{LOGD}/removed_samples.jsonl")

# (1) trùng hoàn toàn train/test ở B2
test_convos = {users(r) for r in load(f"{T}/test_B_B2.jsonl")}
train = load(f"{T}/group_B_B2.jsonl")
keep = []
for i, r in enumerate(train, 1):
    if users(r) in test_convos:
        removed.append({"file": "group_B_B2.jsonl", "line_after_step1": i, "reason": "trùng hoàn toàn chuỗi tin nhắn user với B2-test", "record": r})
        changes.append({"file": "group_B_B2.jsonl", "line": i, "action": "remove_sample(train_test_duplicate)", "field": "", "before": "", "after": ""})
    else:
        keep.append(r)
save(f"{T}/group_B_B2.jsonl", keep)
print("B2 train:", len(train), "->", len(keep))

# (2) chuyển sang safetyguard
MOVE = {
    ("group_B_B1.jsonl", 208): ("khung_hoang", "critical", "nói rõ muốn kết thúc cuộc sống ngay lập tức"),
    ("group_B_B1.jsonl", 341): ("khung_hoang", "critical", "tội lỗi, 'muốn chết đi cho xong' (gián tiếp)"),
    ("group_B_B1.jsonl", 362): ("khung_hoang", "critical", "'muốn biến mất khỏi thế giới này' (gián tiếp)"),
    ("group_B_B1.jsonl", 558): ("khung_hoang", "critical", "nhục nhã 'muốn chết đi cho xong' (gián tiếp)"),
    ("group_B_B1.jsonl", 602): ("khung_hoang", "critical", "hoảng loạn đến mức muốn tự tử"),
    ("group_B_B1.jsonl", 657): ("khung_hoang", "critical", "nhục nhã 'muốn chết đi cho xong' (gián tiếp)"),
    ("group_A_formatted.jsonl", 600): ("thuoc_dieu_tri", "medium", "bắt đầu dùng thuốc để đầu óc chậm lại; có nhắc tự tử nhưng phủ nhận ý định (ca ranh giới)"),
    ("group_A_formatted.jsonl", 1665): ("thuoc_dieu_tri", "low", "phải bắt đầu lại thuốc điều trị sau hóa trị"),
    ("test_A_formatted.jsonl", 697): ("thuoc_dieu_tri", "low", "đang dùng thuốc, lo không đáp ứng thuốc"),
    ("test_B_B1.jsonl", 51): ("thuoc_dieu_tri", "high", "tự uống thuốc hạ áp, đau thắt ngực nhưng chưa đi khám"),
    ("test_B_B1.jsonl", 109): ("thuoc_dieu_tri", "medium", "dùng thuốc an thần sau bỏng độ hai"),
}
sg = load(f"{T}/safetyguard.jsonl")
known = {u for r in sg for m in r["messages"] if m["role"] == "user" for u in [m["content"]]}
nxt = max(int(r["test_id"].split("A")[1]) for r in sg if r.get("test_id")) + 1
added = 0
for x in removed:
    key = (x["file"], x.get("line"))
    if key not in MOVE: continue
    rec = x["record"]
    if any(m["content"] in known for m in rec["messages"] if m["role"] == "user"):
        x["moved_to"] = "safetyguard.jsonl (đã có sẵn)"; continue
    fg, sev, reason = MOVE[key]
    branch = "A" if "_A_" in x["file"] else "B1"
    sg.append({"line_no": x["line"], "flag_group": fg, "severity": sev, "flag_groups": [fg], "reason": reason,
               "test_id": f"TC-A{nxt:04d}", "messages": rec["messages"],
               "metadata": {"cluster_id": None, "branch": branch, "source_file": x["file"]}})
    x["moved_to"] = f"safetyguard.jsonl TC-A{nxt:04d}"
    nxt += 1; added += 1
save(f"{T}/safetyguard.jsonl", sg)
save(f"{LOGD}/removed_samples.jsonl", removed)
save(f"{LOGD}/change_log.jsonl", changes)
print("safetyguard:", len(sg) - added, "->", len(sg))
