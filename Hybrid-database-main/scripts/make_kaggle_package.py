"""BẢN THỬ NGHIỆM (nhánh thu-nghiem/llm1-ngu-canh): đóng gói hệ thống để tải lên Kaggle làm dataset
(không gồm file GGUF 4.7 GB, tải riêng). Tên gói và trường "variant" trong manifest khác bản chính thức, để notebook
không chạy nhầm gói chính thức và không trộn kết quả của hai bản.

    python scripts/make_kaggle_package.py      ->  ../kaggle_upload/huhu-system-thu-nghiem.zip

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
VARIANT = "thu-nghiem/llm1-ngu-canh"
OUT = os.path.join(AIM, "kaggle_upload", "huhu-system-thu-nghiem.zip")

INCLUDE_DIRS = ["backend", "retrieval", "db", "ingestion", "scripts", "serving", "tests", os.path.join("data", "processed")]
INCLUDE_FILES = ["requirements.txt", ".env", "README.md", "docker-compose.yml"]
RENAME = {".env": "dot_env"}  # Kaggle có thể bỏ file ẩn khi giải nén dataset; notebook đổi lại thành .env
SKIP_EXT = {".gguf", ".pyc"}
SKIP_DIRS = {"__pycache__", "logs"}
MODELS = ["qwen-huhu:latest", "qwen2.5:7b-instruct", "gemma3:4b"]
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


def ollama_digests():
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True, encoding="utf-8").stdout
    rows = {line.split()[0]: line.split()[1] for line in out.splitlines()[1:] if line.strip()}
    return {m: rows.get(m) for m in MODELS}


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
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    gguf = os.path.join(ROOT, "serving", "qwen2.5-7b-huhu-Q4_K_M.gguf")
    if not os.path.exists(gguf):  # worktree thử nghiệm không có GGUF: dùng file của bản chính thức (cùng model)
        gguf = os.path.join(os.path.dirname(AIM), "Hybrid-database-main", "serving", "qwen2.5-7b-huhu-Q4_K_M.gguf")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "backend", "retrieval", "db", "ingestion", "scripts",
                            "serving", "tests", "data"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if dirty:
        sys.exit(f"Còn thay đổi chưa commit, hãy commit trước khi đóng gói:\n{dirty}")
    manifest = {"variant": VARIANT, "git_commit": commit,
                "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "gguf_sha256": sha256(gguf),
                "ollama_digests": ollama_digests(), "bge_m3": BGE_M3, "files": {}}
    if None in manifest["ollama_digests"].values():
        sys.exit(f"Thiếu model trong `ollama list`: {manifest['ollama_digests']}")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files():
            arc = os.path.join("AIM", os.path.relpath(p, AIM)).replace(os.sep, "/")
            head, name = arc.rsplit("/", 1)
            arc = f"{head}/{RENAME.get(name, name)}"
            z.write(p, arc)
            manifest["files"][arc] = sha256(p)
        z.writestr("AIM/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"{OUT}: {len(manifest['files'])} file, {os.path.getsize(OUT) / 1e6:.1f} MB")
    print("variant:", VARIANT, "| commit:", commit)
    print("GGUF sha256:", manifest["gguf_sha256"])
    print("Ollama:", manifest["ollama_digests"])


if __name__ == "__main__":
    main()
