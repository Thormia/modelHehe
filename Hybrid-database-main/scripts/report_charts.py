"""Biểu đồ minh hoạ cho BAO_CAO_KET_QUA_CUOI.docx (gọi từ build_final_report.py).

Mỗi hàm nhận số liệu đã tính trong load_all() và trả về đường dẫn PNG; không tự tính lại số nào khác.
"""
import json
import os
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# Bảng màu phân loại cố định theo thứ tự (đã kiểm CVD); mỗi hệ thống luôn giữ một màu.
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SYS_COLOR = dict(zip(("P", "B1", "B2", "B3"), C))
GRAY = "#c9c8c3"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
OUT_DIR = tempfile.mkdtemp(prefix="bao_cao_charts_")

plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": GRID, "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.08,
})
PCT = FuncFormatter(lambda v, _: f"{v:.0f}%")


def vn(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def _axes(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left" if grid == "y" else "bottom"].set_visible(False)
    ax.grid(axis=grid, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _save(fig, name):
    p = os.path.join(OUT_DIR, name)
    fig.savefig(p)
    plt.close(fig)
    return p


def _bar_labels(ax, bars, fmt, horizontal=False):
    for b in bars:
        v = b.get_width() if horizontal else b.get_height()
        if horizontal:
            ax.annotate(fmt(v), (v, b.get_y() + b.get_height() / 2), xytext=(3, 0), textcoords="offset points",
                        va="center", fontsize=8.5, color=INK2)
        else:
            ax.annotate(fmt(v), (b.get_x() + b.get_width() / 2, v), xytext=(0, 2), textcoords="offset points",
                        ha="center", fontsize=8.5, color=INK2)


def effective_by_system(an, systems):
    """Tỷ lệ đạt hiệu quả trên bộ crisis và safety của P và 3 baseline."""
    fig, ax = plt.subplots(figsize=(6.3, 2.9))
    w = 0.36
    xs = range(len(systems))
    for j, (su, label) in enumerate((("crisis", "Khủng hoảng (164 câu)"), ("safety", "An toàn (300 câu)"))):
        vals = [100 * an[s][su]["effective"] / an[s][su]["n"] for s in systems]
        bars = ax.bar([x + (j - 0.5) * (w + 0.02) for x in xs], vals, w, color=C[j], label=label)
        _bar_labels(ax, bars, lambda v: vn(v) + "%")
    ax.set_xticks(list(xs), ["P (đề xuất)", "B1 gốc trực tiếp", "B2 fine-tune trực tiếp", "B3 pipeline + gốc"])
    ax.set_ylim(0, 108)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_ylabel("Đạt hiệu quả")
    _axes(ax)
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.13))
    return _save(fig, "effective.png")


def training_loss(history_path):
    """Train loss (trung bình 10 bước) và val loss toàn bộ theo bước, đánh dấu bước tốt nhất và điểm dừng."""
    d = json.load(open(history_path, encoding="utf-8"))
    tr = d["history"]["train"]
    va = [(s, v["ALL"]) for s, v in d["history"]["val"]]
    best = d["state"]["best_step"]
    fig, ax = plt.subplots(figsize=(6.3, 2.8))
    ax.plot([s for s, _ in tr], [v for _, v in tr], color=C[0], linewidth=1.4, label="Train loss")
    ax.plot([s for s, _ in va], [v for _, v in va], color=C[1], linewidth=2, marker="o", markersize=4, label="Validation loss")
    bv = dict(va)[best]
    ax.annotate(f"tốt nhất {vn(bv, 4)}\n(bước {best})", (best, bv), xytext=(0, 30), textcoords="offset points",
                ha="center", fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    stop = d["state"]["step"]
    ax.axvline(stop, color=INK2, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.text(stop, ax.get_ylim()[1], " early stopping", fontsize=8.5, color=INK2, va="top", ha="right")
    ax.set_xlabel("Bước huấn luyện")
    ax.set_ylabel("Loss")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: vn(v)))
    _axes(ax)
    ax.legend(loc="upper center")
    return _save(fig, "loss.png")


def perplexity(groups, base, ft):
    """Perplexity của model gốc và model fine-tune theo nhóm tập test."""
    fig, ax = plt.subplots(figsize=(6.3, 2.7))
    w = 0.36
    xs = range(len(groups))
    for j, (vals, label) in enumerate(((base, "Qwen2.5-7B gốc"), (ft, "Fine-tune (qwen-huhu)"))):
        bars = ax.bar([x + (j - 0.5) * (w + 0.02) for x in xs], vals, w, color=C[j], label=label)
        _bar_labels(ax, bars, lambda v: vn(v, 2))
    ax.set_xticks(list(xs), groups)
    ax.set_ylabel("Perplexity (thấp hơn là tốt hơn)")
    ax.set_ylim(0, max(base) * 1.15)
    _axes(ax)
    ax.legend(loc="upper left")
    return _save(fig, "perplexity.png")


def crisis_detection(cd, names):
    """LLM #1 phát hiện / bỏ sót theo loại khủng hoảng (thanh ngang chồng, số câu)."""
    keys = list(names)
    fig, ax = plt.subplots(figsize=(6.3, 1.9))
    ys = range(len(keys))[::-1]
    hit = [cd[k]["flag"] for k in keys]
    miss = [cd[k]["n"] - cd[k]["flag"] for k in keys]
    ax.barh(list(ys), hit, 0.55, color=C[0], label="LLM #1 phát hiện", edgecolor="white", linewidth=1)
    ax.barh(list(ys), miss, 0.55, left=hit, color=GRAY, label="Bỏ sót", edgecolor="white", linewidth=1)
    for y, h, m in zip(ys, hit, miss):
        ax.text(h / 2, y, f"{h}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        ax.text(h + m + 0.8, y, f"{vn(100 * h / (h + m))}% ({h}/{h + m})", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(list(ys), [names[k] for k in keys])
    ax.set_xlim(0, max(h + m for h, m in zip(hit, miss)) * 1.3)
    ax.set_xlabel("Số câu")
    _axes(ax, "x")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.45, 1.3))
    return _save(fig, "crisis_detect.png")


def retrieval_extract(cat, keys):
    """Tỷ lệ trích được state và có đích tác động đúng theo nhóm câu truy xuất."""
    fig, ax = plt.subplots(figsize=(6.3, 2.9))
    ys = list(range(len(keys)))[::-1]
    h = 0.38
    a = [100 * cat[k]["any"] / cat[k]["n"] for k in keys]
    b = [100 * cat[k]["hit"] / cat[k]["m"] if cat[k]["m"] else None for k in keys]
    bars = ax.barh([y + h / 2 + 0.01 for y in ys], a, h, color=C[0], label="Trích được state")
    _bar_labels(ax, bars, lambda v: vn(v) + "%", horizontal=True)
    yb = [y - h / 2 - 0.01 for y, v in zip(ys, b) if v is not None]
    bars = ax.barh(yb, [v for v in b if v is not None], h, color=C[1], label="Có đích tác động đúng")
    _bar_labels(ax, bars, lambda v: vn(v) + "%", horizontal=True)
    for y, v in zip(ys, b):
        if v is None:
            ax.text(1, y - h / 2, "không chấm đích", va="center", fontsize=8, color=INK2, style="italic")
    ax.set_yticks(ys, keys)
    ax.set_xlim(0, 112)
    ax.xaxis.set_major_formatter(PCT)
    _axes(ax, "x")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.4, 1.13))
    return _save(fig, "retrieval.png")


def safety_by_trap(an, systems, groups, names):
    """Tỷ lệ đạt hiệu quả theo loại bẫy an toàn, mỗi hệ thống một màu cố định."""
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    ys = list(range(len(groups)))[::-1]
    h = 0.19
    for j, s in enumerate(systems):
        vals = [100 * an[s]["safety"]["by_group"][g]["effective"] / an[s]["safety"]["by_group"][g]["n"] for g in groups]
        off = (1.5 - j) * (h + 0.01)
        bars = ax.barh([y + off for y in ys], vals, h, color=SYS_COLOR[s], label=s)
        _bar_labels(ax, bars, lambda v: vn(v, 0) + "%", horizontal=True)
    ax.set_yticks(ys, [f"{names[g]}\n(n = {an['P']['safety']['by_group'][g]['n']})" for g in groups])
    ax.set_xlim(0, 110)
    ax.xaxis.set_major_formatter(PCT)
    ax.set_xlabel("Đạt hiệu quả")
    _axes(ax, "x")
    ax.legend(loc="upper center", ncol=4, bbox_to_anchor=(0.4, 1.09))
    return _save(fig, "safety_trap.png")


def b3_groups(rows):
    """Hội thoại B3 theo tình trạng người dùng kể: cờ y tế bật → nhánh thuốc / không bật."""
    rows = sorted(rows, key=lambda r: (r[2] / r[1], r[1]))
    fig, ax = plt.subplots(figsize=(6.3, 3.5))
    ys = range(len(rows))
    hit = [r[2] for r in rows]
    miss = [r[1] - r[2] for r in rows]
    ax.barh(list(ys), hit, 0.62, color=C[0], label="Cờ bật → nhánh thuốc", edgecolor="white", linewidth=1)
    ax.barh(list(ys), miss, 0.62, left=hit, color=GRAY, label="Không vào nhánh thuốc", edgecolor="white", linewidth=1)
    for y, hh, m in zip(ys, hit, miss):
        ax.text(hh + m + 0.6, y, f"{hh}/{hh + m}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(list(ys), [r[0] for r in rows])
    ax.set_xlim(0, max(r[1] for r in rows) * 1.15)
    ax.set_xlabel("Số hội thoại")
    _axes(ax, "x")
    ax.legend(loc="lower right")
    return _save(fig, "b3_groups.png")


def expert_likert(items):
    """Điểm trung bình ± SD thang Likert 1–5 theo tiêu chí; items = [(phần, tiêu chí, mean, sd)]."""
    parts = list(dict.fromkeys(p for p, *_ in items))
    color = dict(zip(parts, C))
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    ys = list(range(len(items)))[::-1]
    for y, (p, crit, m, sd) in zip(ys, items):
        # thang chỉ tới 5 nên râu SD được cắt ở 5
        ax.errorbar(m, y, xerr=[[sd], [min(sd, 5 - m)]], fmt="o", color=color[p], markersize=5, elinewidth=1.2, capsize=2)
        ax.text(5.42, y, vn(m, 2), va="center", fontsize=8.5, color=INK2)
    for p in parts:
        ax.plot([], [], "o", color=color[p], label=p)
    ax.set_yticks(ys, [c for _, c, *_ in items])
    ax.set_xlim(3.5, 5.55)
    ax.set_xticks([3.5, 4, 4.5, 5], ["3,5", "4", "4,5", "5"])
    ax.axvline(5, color=INK2, linewidth=0.8)
    ax.set_xlabel("Điểm trung bình ± SD (thang 1–5)")
    _axes(ax, "x")
    ax.legend(loc="upper center", ncol=4, bbox_to_anchor=(0.3, 1.08), fontsize=8.5, handletextpad=0.2, columnspacing=0.8)
    return _save(fig, "expert.png")
