"""Làm sạch generative.jsonl.

1. Chuẩn hoá nhãn trong system message:
   - "MentalState:" -> "Mental State:" (lỗi gõ)
   - bỏ dấu chấm cuối: "Mental State: Stressed." -> "Mental State: Stressed"
2. Xoá record trùng (cùng user + assistant), giữ lần xuất hiện đầu.
3. Đánh lại test_id: TC-A0001, TC-A0002, ...

Chạy (từ thư mục data-generative):
    python -X utf8 fix_generative.py
    python -X utf8 fix_generative.py --input generative_backup_before_fix.jsonl --output generative.jsonl
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def fix(records):
    out, seen, dup_lines = [], set(), []
    for line_no, r in enumerate(records, 1):
        m = r["messages"]
        sys_ = m[0]["content"].strip()
        sys_ = re.sub(r"MentalState:", "Mental State:", sys_)
        sys_ = re.sub(r"(Mental State:\s*[^|.]+?)\.\s*$", r"\1", sys_)
        m[0]["content"] = sys_

        key = (m[1]["content"], m[2]["content"])
        if key in seen:
            dup_lines.append(line_no)
            continue
        seen.add(key)
        out.append({"test_id": f"TC-A{len(out) + 1:04d}", "messages": m})
    return out, dup_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=HERE / "generative_backup_before_fix.jsonl", type=Path)
    ap.add_argument("--output", default=HERE / "generative.jsonl", type=Path)
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    out, dup_lines = fix(records)

    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"input : {args.input.name} ({len(records)} records)")
    print(f"output: {args.output.name} ({len(out)} records)")
    print(f"removed {len(dup_lines)} duplicate lines: {dup_lines}")


if __name__ == "__main__":
    main()
