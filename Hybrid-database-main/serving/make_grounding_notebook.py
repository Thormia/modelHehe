"""Tạo serving/eval_grounding_kaggle.ipynb từ serving/eval_final_kaggle.ipynb: giữ nguyên các cell dựng hạ tầng, kiểm tra
liêm chính, seed và kiểm DB, unit test, chạy thử; thay phần chạy bộ test bằng scripts/eval_grounding.py.

    python serving/make_grounding_notebook.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "eval_final_kaggle.ipynb")
DST = os.path.join(HERE, "eval_grounding_kaggle.ipynb")


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}


def main():
    nb = json.load(open(SRC, encoding="utf-8"))
    cells = nb["cells"]
    cut = next(i for i, c in enumerate(cells) if c["cell_type"] == "markdown" and "## Chạy bộ test" in "".join(c["source"]))
    head = cells[1:cut]  # bỏ markdown giới thiệu của notebook final
    intro = md("""
# Grounding nhánh dinh dưỡng và định tuyến qua nhiều lượt (Kaggle)

Cùng hệ thống, hạ tầng và các bước kiểm tra liêm chính với notebook đánh giá final (`eval_final_kaggle.ipynb`).
Dữ liệu: tập test fine-tune `traindata/test_B_B1..B4.jsonl`, đã tách sẵn từ trước, không lấy từ 3 bộ test 300 ca.
- **Phần A:** grounding mức model trên 240 mẫu B2 (context lấy từ chính mẫu), so `qwen-huhu` với `qwen2.5:7b-instruct` gốc.
- **Phần B:** toàn hệ thống qua các lượt hội thoại B1–B4 (958 hội thoại): đúng nhánh ở lượt cuối; B2 hai lượt (gom đủ state
  qua hội thoại thì vào nhánh dinh dưỡng); so MISSING_STATES; grounding với món lấy từ PostgreSQL.

**Cài đặt:** Accelerator = GPU T4 x2, Internet = On. **Input:** dataset `huhu-system-final` (bản mới nhất) và GGUF như
notebook final. Chạy tiếp: gắn Output của lần chạy trước làm input, ca đã xong được bỏ qua.
""")
    tail = [
        md("""
## Chạy grounding và định tuyến
Pha sinh (A, B) rồi chấm bằng giám khảo `gemma3:4b`.
"""),
        code('sh("python -u scripts/eval_grounding.py gen-a --workers 2", log=f"{APP}/logs/eval/run_grounding_gen_a.txt")'),
        code('sh("python -u scripts/eval_grounding.py gen-b --workers 2", log=f"{APP}/logs/eval/run_grounding_gen_b.txt")'),
        code('sh("python -u scripts/eval_grounding.py score", log=f"{APP}/logs/eval/run_grounding_score.txt")\n'
             'sh("python -u scripts/eval_grounding.py report", log=f"{APP}/logs/eval/run_grounding_report.txt")'),
        code('sh("ollama list > logs/eval/ollama_list_kaggle.txt && nvidia-smi > logs/eval/nvidia_smi_kaggle.txt")\n'
             'shutil.make_archive(f"{W}/eval_grounding_results", "zip", APP, "logs")\n'
             'print(f"{W}/eval_grounding_results.zip", round(os.path.getsize(f"{W}/eval_grounding_results.zip") / 1e6, 1), "MB")'),
    ]
    nb["cells"] = [intro] + head + tail
    json.dump(nb, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(DST, len(nb["cells"]), "cells")


if __name__ == "__main__":
    main()
