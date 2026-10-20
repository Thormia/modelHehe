"""Tổng kết phiếu kiểm chứng dữ liệu với chuyên gia và tính độ đồng thuận giữa người chấm.

    python scripts/expert_agreement.py ../expert_feedback      ->  in Markdown, ghi expert_feedback/agreement.json

Đọc các file expert_review_sheet_*.xlsx (cùng 40 mẫu: 4 sheet x 10). Chuẩn hóa giá trị ("4.0" -> 4, "đạt"/"Đạt", "pass"…),
ô trống = thiếu (không tính).
Chỉ số đồng thuận:
  - Fleiss' kappa (theo kế hoạch idea.docx; chỉ dùng các mẫu đủ mọi người chấm).
  - Krippendorff's alpha (ordinal cho Likert, nominal cho cột chọn; chấp nhận ô thiếu).
  - Gwet's AC2 (trọng số bậc hai, Likert) / AC1 (cột chọn): ổn định khi điểm dồn về một phía (nghịch lý kappa).
  - Tỷ lệ đồng ý theo cặp người chấm: trùng khớp hoàn toàn và lệch không quá 1 điểm.
"""
import glob
import itertools
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

import openpyxl

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# sheet -> (cột bắt đầu chấm, tiêu chí Likert, tiêu chí lựa chọn, cột nhận xét)
SHEETS = {
    "1_FineTune": (4, ["Thấu cảm & công nhận cảm xúc", "Tự nhiên, giọng người bạn", "Chất lượng dịch tiếng Việt", "An toàn"],
                   ["Dùng được để fine-tune (Đạt)"], 9),
    "2_Generative_QA": (5, ["Thấu cảm & chuyển tiếp mượt", "Lời khuyên dinh dưỡng đúng khoa học", "Phù hợp triệu chứng",
                            "Trung thành với context"], ["An toàn y khoa (Pass)", "Cần chuyển tuyến mà chưa nói (Có)"], 11),
    "3_RAG_DinhDuong": (6, ["Thực phẩm giàu chất đã nêu", "Cơ chế tác động đúng khoa học", "Câu văn rõ ràng"],
                        ["Nhãn ontology_effect đúng", "Có phát biểu quá mức (Có)"], 11),
    "4_RAG_TamLy": (5, ["Nội dung đúng chuyên môn tâm lý", "Chất lượng dịch tiếng Việt", "Chunk đủ ngữ cảnh"],
                    ["Nhãn target_mental_state đúng", "Tags phù hợp"], 10),
}
SHEET_NAME = {"1_FineTune": "Dữ liệu fine-tune", "2_Generative_QA": "QA tự sinh (RAG → gợi ý)",
              "3_RAG_DinhDuong": "Kho RAG dinh dưỡng", "4_RAG_TamLy": "Kho RAG tâm lý"}
CAT_MAP = {"đạt": 1, "không đạt": 0, "pass": 1, "fail": 0, "có": 1, "không": 0, "đúng": 1, "sai": 0}
# Cột chọn mà giá trị "tốt" là 0 (Có = vấn đề)
CAT_BAD_IS_ONE = {"Cần chuyển tuyến mà chưa nói (Có)", "Có phát biểu quá mức (Có)"}
RATER_INFO = {  # chuyên môn theo tên file / phần thông tin trong phiếu
    "BacSiDaKhoa": "Bác sĩ đa khoa", "CongNgheSinhHoc": "Cử nhân công nghệ sinh học", "HoaHuuCo": "Công nghệ hóa hữu cơ và hóa dược",
    "YHoc": "Y học", "Yhoc2": "Sinh viên Y dược", "Yhoc3": "Y học",
    "Yhoc4": "Y khoa (bổ sung 18/10)", "Yhoc5": "Y khoa (bổ sung 18/10)",
}


INVALID = []  # (người chấm, sheet, mẫu, tiêu chí, giá trị): ô cột chọn điền điểm 4–5, quy đổi thành Đạt/Đúng


def _num(v):
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def load(folder):
    data = []  # (rater, sheet, item, criterion, kind, value)
    comments = defaultdict(list)
    raters = []
    for f in sorted(glob.glob(os.path.join(folder, "expert_review_sheet_*.xlsx"))):
        rater = os.path.basename(f)[len("expert_review_sheet_"):-5]
        raters.append(rater)
        wb = openpyxl.load_workbook(f, data_only=True)
        for sh, (start, lik, cat, ci) in SHEETS.items():
            for r in wb[sh].iter_rows(min_row=5, values_only=True):
                if not r[0]:
                    continue
                for j, crit in enumerate(lik + cat):
                    v = r[start + j]
                    if v is None or str(v).strip() == "":
                        val = None
                    elif j < len(lik):
                        val = int(float(str(v).strip()))
                    elif str(v).strip().lower() in CAT_MAP:
                        val = CAT_MAP[str(v).strip().lower()]
                    elif crit not in CAT_BAD_IS_ONE and _num(v) is not None and _num(v) >= 4:
                        # Người chấm điền điểm 4–5 vào cột Đạt/Đúng (chấm nội dung, không theo định dạng ô): nhóm quy ước = Đạt/Đúng
                        val = 1
                        INVALID.append((rater, sh, r[0], crit, v))
                    else:  # giá trị khác ngoài danh sách: không đoán, coi là thiếu
                        val = None
                    data.append((rater, sh, r[0], crit, "likert" if j < len(lik) else "cat", val))
                note = " ".join(str(x) for x in r[ci:] if x)
                if note.strip():
                    comments[(sh, r[0])].append((rater, note.strip()))
    return raters, data, comments


# ------------------------------------------------------------------ chỉ số
def units_from(data, raters, keyfilter):
    """unit (sheet, item, criterion) -> {rater: value} (bỏ ô thiếu)."""
    u = defaultdict(dict)
    for rater, sh, item, crit, kind, val in data:
        if keyfilter(sh, crit, kind) and val is not None:
            u[(sh, item, crit)][rater] = val
    return u


def kripp_alpha(units, cats, metric):
    pairable = [list(v.values()) for v in units.values() if len(v) >= 2]
    if not pairable:
        return None
    o = defaultdict(float)
    for vals in pairable:
        m = len(vals)
        for a, b in itertools.permutations(range(m), 2):
            o[(vals[a], vals[b])] += 1 / (m - 1)
    n_c = Counter()
    for (c, k), w in o.items():
        n_c[c] += w
    n = sum(n_c.values())

    def d2(c, k):
        if metric == "nominal":
            return 0.0 if c == k else 1.0
        lo, hi = sorted((c, k))
        s = sum(n_c[g] for g in cats if lo <= g <= hi) - (n_c[lo] + n_c[hi]) / 2
        return s * s
    do = sum(w * d2(c, k) for (c, k), w in o.items())
    de = sum(n_c[c] * n_c[k] * d2(c, k) for c in cats for k in cats) / (n - 1)
    return None if de == 0 else 1 - do / de


def gwet(units, cats, weighted):
    q = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    w = [[1 - ((i - j) / (q - 1)) ** 2 if weighted else float(i == j) for j in range(q)] for i in range(q)]
    rated = [v for v in units.values() if len(v) >= 1]
    pi = [0.0] * q
    for v in rated:
        cnt = Counter(v.values())
        for c, nk in cnt.items():
            pi[idx[c]] += nk / len(v)
    pi = [p / len(rated) for p in pi]
    pa_list = []
    for v in units.values():
        r = len(v)
        if r < 2:
            continue
        cnt = Counter(v.values())
        s = 0.0
        for c, rk in cnt.items():
            rstar = sum(w[idx[c]][idx[l]] * cnt.get(l, 0) for l in cats)
            s += rk * (rstar - 1)
        pa_list.append(s / (r * (r - 1)))
    pa = statistics.mean(pa_list)
    tw = sum(sum(row) for row in w)
    pe = tw / (q * (q - 1)) * sum(p * (1 - p) for p in pi)
    return None if pe == 1 else (pa - pe) / (1 - pe), pa


def fleiss(units, cats, n_raters):
    full = [v for v in units.values() if len(v) == n_raters]
    if len(full) < 2:
        return None, len(full)
    N, n = len(full), n_raters
    p = Counter()
    P = []
    for v in full:
        cnt = Counter(v.values())
        p.update(cnt)
        P.append((sum(c * c for c in cnt.values()) - n) / (n * (n - 1)))
    pj = [p[c] / (N * n) for c in cats]
    Pbar, Pe = statistics.mean(P), sum(x * x for x in pj)
    return (None if Pe == 1 else (Pbar - Pe) / (1 - Pe)), N


def pairwise(units, raters):
    ex = w1 = tot = 0
    for v in units.values():
        for a, b in itertools.combinations(sorted(v), 2):
            tot += 1
            ex += v[a] == v[b]
            w1 += abs(v[a] - v[b]) <= 1
    return ex / tot if tot else None, w1 / tot if tot else None, tot


def agreement(units, cats, kind, n_raters, raters):
    alpha = kripp_alpha(units, cats, "ordinal" if kind == "likert" else "nominal")
    ac, pa = gwet(units, cats, weighted=(kind == "likert"))
    fk, n_full = fleiss(units, cats, n_raters)
    ex, w1, npairs = pairwise(units, raters)
    return {"alpha": alpha, "gwet": ac, "gwet_pa": pa, "fleiss": fk, "fleiss_items": n_full, "exact": ex, "within1": w1,
            "pairs": npairs, "units": len(units)}


def fmt(x, d=2):
    return "–" if x is None else f"{x:.{d}f}"


def main(folder):
    raters, data, comments = load(folder)
    R = len(raters)
    L = [1, 2, 3, 4, 5]
    out = {"raters": raters, "descriptive": {}, "agreement": {},
           "choice_cells_from_score": [{"rater": a, "sheet": b, "item": c, "criterion": d, "value": str(e)} for a, b, c, d, e in INVALID]}
    print(f"# Tổng kết phiếu kiểm chứng dữ liệu với chuyên gia\n")
    if INVALID:
        print(f"Ghi chú: {len(INVALID)} ô ở cột chọn được điền điểm 4–5, quy đổi thành Đạt/Đúng: "
              + "; ".join(f"{a} {c} {d[:30]} = {e}" for a, b, c, d, e in INVALID[:3]) + (" ..." if len(INVALID) > 3 else "") + "\n")
    print(f"{R} người chấm, 40 mẫu (4 phần × 10 mẫu, cùng một bộ mẫu cho mọi người).\n")
    print("| Mã | File | Chuyên môn | Số ô đã chấm |\n|---|---|---|---|")
    for i, r in enumerate(raters, 1):
        n = sum(1 for d in data if d[0] == r and d[5] is not None)
        tot = sum(1 for d in data if d[0] == r)
        print(f"| R{i} | {r} | {RATER_INFO.get(r, '')} | {n}/{tot} |")

    print("\n## 1. Điểm theo tiêu chí\n")
    print("| Phần | Tiêu chí | n | Trung bình ± SD | Trung vị | Tỷ lệ ≥ 4 | Tỷ lệ = 5 | Thấp nhất |")
    print("|---|---|---|---|---|---|---|---|")
    for sh, (_, lik, cat, _) in SHEETS.items():
        for crit in lik:
            v = [d[5] for d in data if d[1] == sh and d[3] == crit and d[5] is not None]
            out["descriptive"][f"{sh}|{crit}"] = {"n": len(v), "mean": statistics.mean(v), "sd": statistics.stdev(v)}
            print(f"| {SHEET_NAME[sh]} | {crit} | {len(v)} | {statistics.mean(v):.2f} ± {statistics.stdev(v):.2f} | "
                  f"{statistics.median(v):g} | {100 * sum(x >= 4 for x in v) / len(v):.0f}% | "
                  f"{100 * sum(x == 5 for x in v) / len(v):.0f}% | {min(v)} |")
    print("\n| Phần | Tiêu chí (cột chọn) | n | Kết quả |\n|---|---|---|---|")
    for sh, (_, lik, cat, _) in SHEETS.items():
        for crit in cat:
            v = [d[5] for d in data if d[1] == sh and d[3] == crit and d[5] is not None]
            ones = sum(v)
            label = "Có" if crit in CAT_BAD_IS_ONE else "Đạt/Đúng/Pass"
            out["descriptive"][f"{sh}|{crit}"] = {"n": len(v), "ones": ones}
            print(f"| {SHEET_NAME[sh]} | {crit} | {len(v)} | {label}: {ones}/{len(v)} ({100 * ones / len(v):.1f}%) |")

    print("\n## 2. Độ đồng thuận giữa người chấm\n")
    print("Đơn vị chấm = (mẫu, tiêu chí). Gộp theo phần vì mỗi tiêu chí chỉ có 10 mẫu.\n")
    print("| Phạm vi | Loại | Số đơn vị | Fleiss' κ (số mẫu đủ người chấm) | Krippendorff's α | Gwet's AC2/AC1 | "
          "Đồng ý hoàn toàn (cặp) | Lệch ≤ 1 điểm (cặp) |")
    print("|---|---|---|---|---|---|---|---|")
    scopes = [(SHEET_NAME[sh], (lambda s: (lambda sh2, c, k: sh2 == s))(sh)) for sh in SHEETS] + [("Tất cả", lambda sh2, c, k: True)]
    for name, flt in scopes:
        for kind, cats in (("likert", L), ("cat", [0, 1])):
            u = units_from(data, raters, lambda sh2, c, k: flt(sh2, c, k) and k == kind)
            if not u:
                continue
            a = agreement(u, cats, kind, R, raters)
            out["agreement"][f"{name}|{kind}"] = a
            print(f"| {name} | {'Likert 1–5' if kind == 'likert' else 'Cột chọn'} | {a['units']} | "
                  f"{fmt(a['fleiss'])} ({a['fleiss_items']}) | {fmt(a['alpha'])} | {fmt(a['gwet'])} | "
                  f"{100 * a['exact']:.1f}% | " + (f"{100 * a['within1']:.1f}% |" if kind == "likert" else "– |"))

    print("\n### Theo từng tiêu chí Likert (10 mẫu mỗi tiêu chí, chỉ để tham khảo)\n")
    print("| Phần | Tiêu chí | Krippendorff's α | Gwet's AC2 | Đồng ý hoàn toàn | Lệch ≤ 1 |")
    print("|---|---|---|---|---|---|")
    for sh, (_, lik, _, _) in SHEETS.items():
        for crit in lik:
            u = units_from(data, raters, lambda sh2, c, k: sh2 == sh and c == crit)
            a = agreement(u, L, "likert", R, raters)
            out["agreement"][f"{sh}|{crit}"] = a
            print(f"| {SHEET_NAME[sh]} | {crit} | {fmt(a['alpha'])} | {fmt(a['gwet'])} | {100 * a['exact']:.0f}% | "
                  f"{100 * a['within1']:.0f}% |")

    print("\n## 3. Mức độ chấm của từng người (Likert, mọi phần)\n")
    print("| Mã | Trung bình | Tỷ lệ cho 5 điểm | Số ô Likert đã chấm |\n|---|---|---|---|")
    for i, r in enumerate(raters, 1):
        v = [d[5] for d in data if d[0] == r and d[4] == "likert" and d[5] is not None]
        print(f"| R{i} | {statistics.mean(v):.2f} | {100 * sum(x == 5 for x in v) / len(v):.0f}% | {len(v)} |")

    print("\n## 4. Mẫu có điểm trung bình thấp nhất (Likert, trung bình mọi tiêu chí và người chấm)\n")
    per = defaultdict(list)
    for d in data:
        if d[4] == "likert" and d[5] is not None:
            per[(d[1], d[2])].append(d[5])
    low = sorted(per.items(), key=lambda kv: statistics.mean(kv[1]))[:8]
    print("| Mẫu | Trung bình | Số nhận xét |\n|---|---|---|")
    for (sh, item), v in low:
        print(f"| {item} | {statistics.mean(v):.2f} | {len(comments.get((sh, item), []))} |")
    out["comments"] = {f"{k[0]}|{k[1]}": v for k, v in comments.items()}
    with open(os.path.join(folder, "agreement.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "expert_feedback"))
