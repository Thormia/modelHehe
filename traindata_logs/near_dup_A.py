"""Đo gần trùng của nhóm A: cosine ≥ 0,9 trên embedding bge-m3 (chuẩn hoá) của tin nhắn user (idea.docx).

    python -I -X utf8 traindata_logs/near_dup_A.py      (từ thư mục C:/FPT/AIM)  ->  traindata_logs/near_dup_A.json

Văn bản của một mẫu = nối các tin nhắn user theo thứ tự. Đo trên hai mốc:
  - nguồn: data/data-finetune/finalfinetune.jsonl (trước lọc an toàn, làm sạch, lọc gần trùng)
  - bản cuối: traindata/group_A_formatted.jsonl (A-train) + traindata/test_A_formatted.jsonl (A-test)
Cụm gần trùng = thành phần liên thông của đồ thị nối các cặp cosine ≥ ngưỡng; "cần bỏ" = tổng (kích thước cụm − 1).
"""
import json
import os
import sys
from collections import Counter

import numpy as np

THRESHOLD = 0.9
SRC = "data/data-finetune/finalfinetune.jsonl"
TRAIN = "traindata/group_A_formatted.jsonl"
TEST = "traindata/test_A_formatted.jsonl"
OUT = "traindata_logs/near_dup_A.json"


def user_texts(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out.append(" ".join(m["content"].strip() for m in r["messages"] if m["role"] == "user"))
    return out


def embed(texts):
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer("BAAI/bge-m3", device=dev, model_kwargs={"use_safetensors": True})
    if dev == "cuda":
        m.half()
    m.max_seq_length = 512
    return np.asarray(m.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)


def pairs(a, b=None, thr=THRESHOLD, chunk=1024):
    """Các cặp (i, j, cos) có cos ≥ thr; b None = trong cùng tập (i < j)."""
    same = b is None
    b = a if same else b
    out = []
    for s in range(0, len(a), chunk):
        sim = a[s:s + chunk] @ b.T
        ii, jj = np.nonzero(sim >= thr)
        for i, j in zip(ii, jj):
            i += s
            if same and j <= i:
                continue
            out.append((int(i), int(j), float(sim[i - s, j])))
    return out


def clusters(n, prs):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, j, _ in prs:
        parent[find(i)] = find(j)
    size = Counter(find(i) for i in range(n))
    big = [s for s in size.values() if s > 1]
    return {"n_clusters": len(big), "samples_in_clusters": sum(big), "to_remove": sum(s - 1 for s in big),
            "largest_cluster": max(big) if big else 0}


def summarize(name, texts, emb):
    prs = pairs(emb)
    exact = len(texts) - len(set(texts))
    c = clusters(len(texts), prs)
    r = {"n": len(texts), "exact_duplicate_texts": exact, "pairs_ge_thr": len(prs), **c,
         "kept_after_dedup": len(texts) - c["to_remove"]}
    print(f"{name}: n={r['n']}, trùng hoàn toàn {exact}, cặp cos≥{THRESHOLD} {len(prs)}, "
          f"{c['n_clusters']} cụm ({c['samples_in_clusters']} mẫu), cần bỏ {c['to_remove']} → còn {r['kept_after_dedup']}")
    return r, prs


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    src, tr, te = user_texts(SRC), user_texts(TRAIN), user_texts(TEST)
    emb = embed(src + tr + te)
    e_src, e_tr, e_te = emb[:len(src)], emb[len(src):len(src) + len(tr)], emb[len(src) + len(tr):]
    res = {"threshold": THRESHOLD, "model": "BAAI/bge-m3 (normalize, fp16 trên GPU)", "text": "nối các tin nhắn user"}
    res["source"], _ = summarize("Nguồn (finalfinetune.jsonl)", src, e_src)
    res["final_A_train"], _ = summarize("A-train cuối", tr, e_tr)
    res["final_A_test"], _ = summarize("A-test cuối", te, e_te)
    cross = pairs(e_tr, e_te)
    res["final_train_test_pairs_ge_thr"] = len(cross)
    res["final_test_with_train_neighbor"] = len({j for _, j, _ in cross})
    res["final_train_test_examples"] = [{"train_line": i + 1, "test_line": j + 1, "cos": round(c, 4),
                                         "train": tr[i][:160], "test": te[j][:160]}
                                        for i, j, c in sorted(cross, key=lambda x: -x[2])[:10]]
    allf = np.concatenate([e_tr, e_te])
    res["final_A_all"], _ = summarize("A cuối (train + test)", tr + te, allf)
    print(f"Cặp A-train × A-test cos≥{THRESHOLD}: {len(cross)}; số mẫu A-test có láng giềng gần trùng trong A-train: "
          f"{res['final_test_with_train_neighbor']}/{len(te)}")
    # Phân bố cosine láng giềng gần nhất (bản cuối), để xem ngưỡng 0,9 nằm ở đâu
    sim = allf @ allf.T
    np.fill_diagonal(sim, -1)
    nn = sim.max(1)
    res["final_nn_cos_quantiles"] = {q: round(float(np.quantile(nn, q)), 4) for q in (0.5, 0.9, 0.99, 1.0)}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(OUT)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
