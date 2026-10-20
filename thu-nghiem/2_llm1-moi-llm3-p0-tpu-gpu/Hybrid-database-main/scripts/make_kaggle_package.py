"""Đóng gói hệ thống final để tải lên Kaggle làm dataset (không gồm file GGUF 4.7 GB, tải riêng).

    python scripts/make_kaggle_package.py --gpu  ->  ../kaggle_upload/huhu-system-gpu.zip     (GPU T4x2, Ollama)
    python scripts/make_kaggle_package.py --tpu  ->  ../kaggle_upload/huhu-system-tpu.zip     (TPU, vLLM)
    python scripts/make_kaggle_package.py        ->  ../kaggle_upload/huhu-system-final.zip   (bản cũ, 3 model Ollama)

Bản GPU và TPU kèm cây code cũ (P0, baseline của hệ thống final) ở AIM/p_old.

Bản TPU kèm LoRA adapter (best_adapter) để gộp vào Qwen2.5-7B-Instruct bf16 trên Kaggle, và ghi revision các model
Hugging Face cùng phiên bản vllm-tpu thay cho GGUF và digest Ollama.

Trong zip: AIM/Hybrid-database-main (code, data/processed, tests, serving trừ .gguf, .env), AIM/data/300 test và
AIM/traindata (cho unit test đối chiếu system prompt với dữ liệu fine-tune).
manifest.json ghi sha256 từng file, sha256 của GGUF và digest các model Ollama ở máy local, để notebook trên Kaggle
kiểm tra hệ thống chạy trên Kaggle giống hệt bản local trước khi chạy test.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIM = os.path.dirname(ROOT)
OUT = os.path.join(AIM, "kaggle_upload", "huhu-system-final.zip")

INCLUDE_DIRS = ["backend", "retrieval", "db", "ingestion", "scripts", "serving", "tests", os.path.join("data", "processed")]
INCLUDE_FILES = ["requirements.txt", ".env", "README.md", "docker-compose.yml"]
RENAME = {".env": "dot_env"}  # Kaggle có thể bỏ file ẩn khi giải nén dataset; notebook đổi lại thành .env
SKIP_EXT = {".gguf", ".pyc"}
SKIP_DIRS = {"__pycache__", "logs"}
MODELS = ["qwen-huhu:latest", "qwen2.5:7b-instruct", "gemma3:12b", "gemma3:4b"]
ADAPTER = os.path.join(AIM, "results", "output", "best_adapter")
# Bản TPU: model Hugging Face (bf16) ghim revision; Gemma 3 lấy từ Kaggle Models nếu có, không thì từ HF (cần HF_TOKEN)
HF_MODELS = {"ext": ("Qwen/Qwen2.5-7B-Instruct", "a09a35458c702b33eeacc393d103063234e8bc28"),
             "check": ("google/gemma-3-12b-it", "96b6f1eccf38110c56df3a15bffe176da04bfd80"),
             "judge": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767")}
VLLM_TPU = "vllm-tpu==0.30.0"
# P0: hệ thống cũ (bản trong báo cáo kết quả lần trước), làm baseline cho hệ thống final; đóng gói từ git vào AIM/p_old
P_OLD_COMMIT = "69532354816ef48efc3a444feffd65fc8404a746"
P_OLD_DIRS = ["backend", "retrieval", "db", "scripts"]


def old_files():
    """(đường dẫn trong zip, nội dung) của cây code cũ, lấy thẳng từ git ở P_OLD_COMMIT."""
    names = subprocess.run(["git", "ls-tree", "-r", "--name-only", P_OLD_COMMIT, "--", *P_OLD_DIRS],
                           capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=True).stdout.split("\n")
    for n in filter(None, names):
        data = subprocess.run(["git", "show", f"{P_OLD_COMMIT}:./{n}"], capture_output=True, cwd=ROOT, check=True).stdout
        yield f"AIM/p_old/Hybrid-database-main/{n}", data
# Bản BAAI/bge-m3 đã dùng để seed ở local: cấu hình + tokenizer từ main, trọng số model.safetensors từ nhánh chuyển đổi
# refs/pr/130 (main không có safetensors; sentence-transformers tự lấy file này khi use_safetensors=True)
BGE_M3 = {"revision": "5617a9f61b028005a4858fdac845db406aefb181",
          "safetensors_revision": "9a0624b896d81da7492a910ffa53731274b6cf3d",
          "safetensors_sha256": "993b2248881724788dcab8c644a91dfd63584b6e5604ff2037cb5541e1e38e7e"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ollama_digests(models):
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True, encoding="utf-8").stdout
    rows = {line.split()[0]: line.split()[1] for line in out.splitlines()[1:] if line.strip()}
    return {m: rows.get(m) or registry_digest(m) for m in models}


def registry_digest(model):
    """ID mà `ollama list` sẽ hiện sau khi pull (12 ký tự đầu sha256 của manifest trên registry.ollama.ai), cho model
    chưa có ở máy local; đã đối chiếu khớp với gemma3:4b và qwen2.5:7b-instruct đang có ở local."""
    import urllib.request
    if model.startswith("qwen-huhu"):
        return None  # model tự tạo từ GGUF, chỉ có ở local
    name, tag = model.split(":")
    req = urllib.request.Request(f"https://registry.ollama.ai/v2/library/{name}/manifests/{tag}",
                                 headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return hashlib.sha256(r.read()).hexdigest()[:12]


def files():
    for d in INCLUDE_DIRS:
        for base, dirs, names in os.walk(os.path.join(ROOT, d)):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for n in names:
                if os.path.splitext(n)[1] not in SKIP_EXT:
                    yield os.path.join(base, n)
    for f in INCLUDE_FILES:
        if os.path.exists(os.path.join(ROOT, f)):
            yield os.path.join(ROOT, f)
    for d in (os.path.join(AIM, "data", "300 test"), os.path.join(AIM, "traindata")):  # traindata: unit test đối chiếu prompt
        for n in sorted(os.listdir(d)):
            if os.path.isfile(os.path.join(d, n)):
                yield os.path.join(d, n)


def main():
    tpu, gpu = "--tpu" in sys.argv[1:], "--gpu" in sys.argv[1:]
    out = os.path.join(AIM, "kaggle_upload", "huhu-system-tpu.zip" if tpu else "huhu-system-gpu.zip" if gpu else
                       os.path.basename(OUT))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    manifest = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "bge_m3": BGE_M3, "files": {}}
    if tpu:
        manifest.update(variant="tpu", hf_models={k: {"repo": r, "revision": v} for k, (r, v) in HF_MODELS.items()},
                        vllm_tpu=VLLM_TPU, p_old_commit=P_OLD_COMMIT)
        extra = [os.path.join(ADAPTER, n) for n in sorted(os.listdir(ADAPTER))]
    else:
        gguf = os.path.join(ROOT, "serving", "qwen2.5-7b-huhu-Q4_K_M.gguf")
        manifest.update(gguf_sha256=sha256(gguf), ollama_digests=ollama_digests(MODELS if gpu else MODELS[:1] + MODELS[1:2] + MODELS[3:]))
        if gpu:
            manifest.update(variant="gpu", p_old_commit=P_OLD_COMMIT)
        if None in manifest["ollama_digests"].values():
            sys.exit(f"Thiếu model trong `ollama list`: {manifest['ollama_digests']}")
        extra = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in list(files()) + extra:
            arc = os.path.join("AIM", os.path.relpath(p, AIM)).replace(os.sep, "/")
            head, name = arc.rsplit("/", 1)
            arc = f"{head}/{RENAME.get(name, name)}"
            z.write(p, arc)
            manifest["files"][arc] = sha256(p)
        if tpu or gpu:
            for arc, data in old_files():
                z.writestr(arc, data)
                manifest["files"][arc] = hashlib.sha256(data).hexdigest()
        z.writestr("AIM/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"{out}: {len(manifest['files'])} file, {os.path.getsize(out) / 1e6:.1f} MB")
    for k in ("gguf_sha256", "ollama_digests", "hf_models", "vllm_tpu"):
        if k in manifest:
            print(f"{k}:", manifest[k])


if __name__ == "__main__":
    main()
