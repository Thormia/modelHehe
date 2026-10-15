"""Kiểm độ nhất quán của giám khảo giữa 2 máy: chấm lại ở local một mẫu câu trả lời mà giám khảo đã chấm trên Kaggle.

    python scripts/judge_consistency.py ../eval_final_results [--every 3]

Lấy cách đều theo thứ tự id (mỗi --every ca lấy 1) các ca safety của hệ thống P ở lần chạy final, chấm lại bằng đúng
eval_system.score_safety (cùng prompt, cùng JUDGE_MODEL, nhiệt độ 0), so cờ của giám khảo và kết quả đạt/không đạt.
"""
import argparse
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from backend import config  # noqa: E402
from backend.llm import LLMClient  # noqa: E402
from eval_system import load, score_safety  # noqa: E402

FLAGS = ("gives_dosage", "gives_diagnosis", "endorses_self_medication_change")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default=os.path.join(os.path.dirname(ROOT), "eval_final_results"))
    ap.add_argument("--every", type=int, default=3)
    a = ap.parse_args()
    items = {it["id"]: it for it in load("test_safety_and_clinical_boundary_vi.json", 0)}
    with open(os.path.join(a.results, "logs", "eval", "baselines", "P_safety_scored.jsonl"), encoding="utf-8") as f:
        rows = sorted((json.loads(l) for l in f if l.strip()), key=lambda r: r["id"])
    sample = rows[::a.every]
    judge = LLMClient(config.JUDGE_BASE_URL, config.JUDGE_MODEL, config.JUDGE_API_KEY, config.LLM_TIMEOUT)
    out = []
    for r in sample:
        checks, v, _ = score_safety(items[r["id"]], r["reply"], judge)
        out.append({"id": r["id"], "kaggle_judge": {k: r["judge"].get(k) for k in FLAGS}, "local_judge": {k: v.get(k) for k in FLAGS},
                    "kaggle_checks": r["checks"], "local_checks": checks,
                    "kaggle_pass": r["correct"], "local_pass": all(checks.values())})
    n = len(out)
    print(f"Giám khảo {config.JUDGE_MODEL}: {n} ca safety (mỗi {a.every} ca lấy 1 theo thứ tự id) chấm lại ở local so với Kaggle\n")
    print("| Cờ của giám khảo | Trùng khớp | Kaggle bật / local bật |\n|---|---|---|")
    for k in FLAGS:
        same = sum(o["kaggle_judge"][k] == o["local_judge"][k] for o in out)
        print(f"| {k} | {same}/{n} ({100 * same / n:.1f}%) | {sum(o['kaggle_judge'][k] is True for o in out)} / "
              f"{sum(o['local_judge'][k] is True for o in out)} |")
    same = sum(o["kaggle_pass"] == o["local_pass"] for o in out)
    print(f"| **Kết quả đạt cả 5 tiêu chí** | **{same}/{n} ({100 * same / n:.1f}%)** | đạt: {sum(o['kaggle_pass'] for o in out)} / "
          f"{sum(o['local_pass'] for o in out)} |")
    diff = [o for o in out if o["kaggle_judge"] != o["local_judge"] or o["kaggle_pass"] != o["local_pass"]]
    for o in diff:
        print(f"- {o['id']}: Kaggle {o['kaggle_judge']} đạt={o['kaggle_pass']} | local {o['local_judge']} đạt={o['local_pass']}")
    with open(os.path.join(ROOT, "logs", "eval", "judge_consistency.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
