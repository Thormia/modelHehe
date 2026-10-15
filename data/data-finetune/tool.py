import json, re, random, sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
CLEAN = BASE.parent / "clean"
SRC, OUT, DONE, TODO = BASE / "src", BASE / "out", BASE / "done", BASE / "todo"
ATTEMPTS_F = BASE / "attempts.json"
MANUAL_F = BASE / "needs_manual.csv"
CHUNK = 150
MAX_ATTEMPTS = 3  # lượt đầu + 2 lượt retry

EN_STOP = set("the a an and or but is are was were be been am i you he she it we they to of in on at for with that this my your his her our their not do does did have has had will would can could just so very really".split())
CASUAL_LABEL = re.compile(r"(?<!\w)(tao|mày|tớ|cậu|mi|bây|tụi mày)(?!\w)", re.I)
LAW_OK = re.compile(r"lawyer|attorney|\blaw\b|legal|court|solicitor", re.I)
HTML_BAD = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>|&nbsp;|&amp;|[♪♫]")


def read_jsonl(p):
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                rows.append({"_bad_json": line[:80]})
    return rows


def write_jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_json(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def prepare():
    for d in (SRC, OUT, DONE, TODO):
        d.mkdir(exist_ok=True)
    all_rows = {}
    for split in ("train", "test"):
        df = pd.read_parquet(CLEAN / f"{split}_final.parquet")
        rows = [{"id": f"{split}_{i:05d}", "input": str(r.input), "label": str(r.label)} for i, r in enumerate(df.itertuples())]
        all_rows[split] = rows
        for c in range(0, len(rows), CHUNK):
            p = SRC / f"{split}_c{c // CHUNK:03d}.jsonl"
            if not p.exists():
                write_jsonl(p, rows[c:c + CHUNK])
    pilot = SRC / "pilot.jsonl"
    if not pilot.exists():
        rng = random.Random(42)
        pool = all_rows["train"]
        def pick(cond, k, used):
            c = [r for r in pool if r["id"] not in used and cond(r)]
            got = rng.sample(c, min(k, len(c)))
            used.update(r["id"] for r in got)
            return got
        used, sel = set(), []
        sel += pick(lambda r: len(r["label"]) < 60, 30, used)
        sel += pick(lambda r: len(r["label"]) > 250, 30, used)
        sel += pick(lambda r: re.search(r"gonna|gotta|lol|kinda|wanna|\bya\b|dude|crap|damn", r["input"] + r["label"], re.I), 20, used)
        sel += pick(lambda r: re.search(r"suicid|kill myself|abuse|self.harm|overdose|drunk|drugs?\b", r["input"] + r["label"], re.I), 10, used)
        sel += pick(lambda r: re.search(r"\d|\$", r["input"] + r["label"]), 10, used)
        write_jsonl(pilot, sel)
    print("prepare OK:", len(list(SRC.glob("*_c*.jsonl"))), "chunks +pilot")


def check_field(en, vi, label=False):
    errs = []
    if not isinstance(vi, str) or not vi.strip():
        return ["rỗng"]
    if HTML_BAD.search(vi) and not HTML_BAD.search(en):
        errs.append("html/ký tự rác")
    toks = re.findall(r"\w+", vi.lower())
    for i in range(len(toks) - 3):
        if toks[i] == toks[i + 1] == toks[i + 2] == toks[i + 3]:
            errs.append("lặp từ"); break
    else:
        for n in (2, 3, 4):
            if any(toks[i:i + n] == toks[i + n:i + 2 * n] == toks[i + 2 * n:i + 3 * n] for i in range(len(toks) - 3 * n + 1)):
                errs.append("lặp cụm"); break
    if "luật sư" in vi.lower() and not LAW_OK.search(en):
        errs.append("luật sư (sai counselor)")
    if len(en) >= 25:
        ratio = len(vi) / len(en)
        if not 0.6 <= ratio <= 2.6:
            errs.append(f"tỉ lệ độ dài {ratio:.2f}")
    elif len(vi) > 150:
        errs.append("quá dài so với gốc")
    if len(toks) >= 4:
        sw = sum(t in EN_STOP for t in toks)
        if sw >= 4 and sw / len(toks) > 0.25:
            errs.append("còn nhiều tiếng Anh")
    for n in set(re.findall(r"\d+(?:[.,]\d+)?", en)):
        if n not in vi and n.replace(",", "") not in vi.replace(",", ""):
            errs.append(f"mất số {n}"); break
    if len(en) > 40 and en.rstrip()[-1] in ".!?\"')”’" and vi.rstrip()[-1].isalnum():
        errs.append("nghi cắt cụt")
    if label and CASUAL_LABEL.search(vi) and not CASUAL_LABEL.search(en):
        errs.append("label xưng hô suồng sã")
    return errs


def chunk_names():
    return sorted(p.stem for p in SRC.glob("*.jsonl"))


def validate(name):
    src = read_jsonl(SRC / f"{name}.jsonl")
    src_by = {r["id"]: r for r in src}
    files = sorted(OUT.glob(f"{name}*.jsonl"), key=lambda p: p.stat().st_mtime)
    good, reasons = {}, {}
    if (DONE / f"{name}.jsonl").exists():
        for r in read_jsonl(DONE / f"{name}.jsonl"):
            good[r["id"]] = r
    for f in files:
        for r in read_jsonl(f):
            rid = r.get("id")
            if rid not in src_by:
                continue
            s = src_by[rid]
            if "input_vi" not in r and "input" in r: r["input_vi"] = r["input"]
            if "label_vi" not in r and "label" in r: r["label_vi"] = r["label"]
            errs = check_field(s["input"], r.get("input_vi"), False) + check_field(s["label"], r.get("label_vi"), True)
            if errs:
                reasons[rid] = "; ".join(errs)
            else:
                good[rid] = {"id": rid, "input_vi": r["input_vi"], "label_vi": r["label_vi"], "flag": r.get("flag")}
                reasons.pop(rid, None)
    for rid in list(reasons):
        if rid in good:
            reasons.pop(rid)
    missing = [i for i in src_by if i not in good]
    write_jsonl(DONE / f"{name}.jsonl", [good[i] for i in src_by if i in good])
    for f in files:
        f.rename(f.with_name(f.name + ".checked"))
    attempts = load_json(ATTEMPTS_F, {})
    if files:
        attempts[name] = attempts.get(name, 0) + 1
    ATTEMPTS_F.write_text(json.dumps(attempts), encoding="utf-8")
    todo_p = TODO / f"{name}.jsonl"
    if not missing:
        todo_p.unlink(missing_ok=True)
        print(f"{name}: XONG {len(good)}/{len(src)}")
        return
    if name != "pilot" and attempts.get(name, 0) >= MAX_ATTEMPTS:
        old = pd.read_csv(MANUAL_F) if MANUAL_F.exists() else pd.DataFrame(columns=["id", "reason"])
        new = pd.DataFrame([{"id": i, "reason": reasons.get(i, "không có bản dịch")} for i in missing])
        pd.concat([old, new]).drop_duplicates("id").to_csv(MANUAL_F, index=False, encoding="utf-8-sig")
        todo_p.unlink(missing_ok=True)
        print(f"{name}: đóng, {len(missing)} dòng chuyển needs_manual.csv")
        return
    write_jsonl(todo_p, [dict(src_by[i], retry_reason=reasons.get(i, "thiếu/JSON hỏng")) for i in missing])
    print(f"{name}: {len(good)}/{len(src)} tốt, {len(missing)} cần dịch lại -> todo/{name}.jsonl (lượt {attempts.get(name, 0)}/{MAX_ATTEMPTS})")


def is_closed(name):
    src = {r["id"] for r in read_jsonl(SRC / f"{name}.jsonl")}
    done = {r["id"] for r in read_jsonl(DONE / f"{name}.jsonl")} if (DONE / f"{name}.jsonl").exists() else set()
    manual = set(pd.read_csv(MANUAL_F)["id"]) if MANUAL_F.exists() else set()
    return src <= (done | manual)


def next_jobs(n):
    fresh, retry = [], []
    for name in chunk_names():
        if name == "pilot" or is_closed(name):
            continue
        todo_p = TODO / f"{name}.jsonl"
        attempt = load_json(ATTEMPTS_F, {}).get(name, 0)
        if todo_p.exists():
            retry.append((name, str(todo_p), str(OUT / f"{name}_r{attempt}_p")))
        else:
            fresh.append((name, str(SRC / f"{name}.jsonl"), str(OUT / f"{name}_p")))
    for j in (fresh + retry)[:n]:
        print("	".join(j))


def status():
    names = [n for n in chunk_names() if n != "pilot"]
    closed = [n for n in names if is_closed(n)]
    retry = [n for n in names if (TODO / f"{n}.jsonl").exists()]
    rows_done = sum(len(read_jsonl(f)) for f in DONE.glob("*.jsonl") if f.name != "pilot.jsonl")
    manual = len(pd.read_csv(MANUAL_F)) if MANUAL_F.exists() else 0
    approved = (BASE / "PILOT_APPROVED").exists()
    pilot_done = (DONE / "pilot.jsonl").exists() and is_closed("pilot") if (SRC / "pilot.jsonl").exists() else False
    txt = (f"# TIẾN ĐỘ DỊCH (tự sinh bởi tool.py status)\n\n"
           f"- Pilot 100 dòng: {'đã dịch xong' if pilot_done else 'CHƯA xong'}; user duyệt: {'CÓ' if approved else 'CHƯA'}\n"
           f"- Chunk đóng: {len(closed)}/{len(names)}\n- Dòng dịch tốt: {rows_done}\n"
           f"- Chunk đang chờ retry: {len(retry)} {retry[:10]}\n- Dòng chuyển needs_manual: {manual}\n"
           f"- Chunk chưa làm: {len(names) - len(closed) - len(retry)}\n")
    (BASE / "PROGRESS.md").write_text(txt, encoding="utf-8")
    print(txt)


def all_src():
    d = {}
    for folder in (SRC, BASE / "src_old"):
        for f in folder.glob("*.jsonl"):
            if f.name != "pilot.jsonl":
                for r in read_jsonl(f):
                    d[r["id"]] = r
    return d


def scope():
    """Chỉ dịch dòng có label >= 150 ký tự (kiểu counselor). Dòng đã dịch tốt được giữ lại."""
    old = BASE / "src_old"
    old.mkdir(exist_ok=True)
    for f in list(SRC.glob("*_c*.jsonl")):
        if not f.name.startswith("sel_"):
            f.rename(old / f.name)
    for f in TODO.glob("*.jsonl"):
        if not f.name.startswith("sel_") and f.name != "pilot.jsonl":
            f.unlink()
    have = {r["id"] for f in DONE.glob("*.jsonl") if f.name != "pilot.jsonl" for r in read_jsonl(f)}
    src = all_src()
    todo = [r for i, r in src.items() if len(r["label"]) >= 150 and i not in have]
    todo.sort(key=lambda r: r["id"])
    for c in range(0, len(todo), CHUNK):
        p = SRC / f"sel_c{c // CHUNK:03d}.jsonl"
        if not p.exists():
            write_jsonl(p, todo[c:c + CHUNK])
    print("scope OK:", len(todo), "dòng còn phải dịch ->", len(list(SRC.glob("sel_c*.jsonl"))), "chunk; đã có sẵn", len(have), "dòng dịch tốt")


def merge():
    names = [n for n in chunk_names() if n != "pilot"]
    open_ = [n for n in names if not is_closed(n)]
    if open_:
        print("CHƯA merge được, còn", len(open_), "chunk chưa đóng:", open_[:10]); return
    src = all_src()
    done = {}
    for f in DONE.glob("*.jsonl"):
        if f.name != "pilot.jsonl":
            for r in read_jsonl(f):
                done[r["id"]] = r
    frames = []
    for split in ("train", "test"):
        rows = [{"id": i, "input_en": src[i]["input"], "label_en": src[i]["label"], "input_vi": d["input_vi"], "label_vi": d["label_vi"], "flag": d.get("flag")}
                for i, d in sorted(done.items()) if i.startswith(split) and i in src]
        df = pd.DataFrame(rows)
        df.to_parquet(BASE / f"{split}_vi.parquet", index=False)
        df.to_csv(BASE / f"{split}_vi.csv", index=False, encoding="utf-8-sig")
        print(split, len(df), "dòng ->", f"{split}_vi.parquet/.csv")
        frames.append(df)
    allrows = pd.concat(frames)
    allrows.sample(min(200, len(allrows)), random_state=7).to_csv(BASE / "spot_check.csv", index=False, encoding="utf-8-sig")
    print("spot_check.csv (200 cặp ngẫu nhiên) đã tạo")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "prepare": prepare()
    elif cmd == "validate":
        for n in (chunk_names() if sys.argv[2] == "--all" else sys.argv[2:]):
            if any(OUT.glob(f"{n}*.jsonl")):
                validate(n)
    elif cmd == "next": next_jobs(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "status": status()
    elif cmd == "merge": merge()
    elif cmd == "scope": scope()
    else: print("prepare | validate <name...|--all> | next [n] | status | merge")
