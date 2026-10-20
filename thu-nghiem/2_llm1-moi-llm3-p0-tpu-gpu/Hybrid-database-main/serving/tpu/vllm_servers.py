"""Chạy các model của hệ thống bằng vLLM trên Kaggle TPU v5e-8 (8 chip, 16 GB HBM mỗi chip), API tương thích OpenAI.

Mỗi model một server vLLM riêng, mỗi server giữ 2 chip (biến môi trường TPU_* chia chip cho từng process):

| server | model                                  | tên phục vụ (giống tag Ollama) | cổng | chip |
| ext    | Qwen2.5-7B-Instruct (LLM #1, B1, B3)   | qwen2.5:7b-instruct            | 8001 | 0,1  |
| gen    | qwen-huhu, LoRA đã gộp, bf16 (LLM #2)  | qwen-huhu                      | 8002 | 2,3  |
| check  | gemma-3-12b-it (LLM #3)                | gemma3:12b                     | 8003 | 4,5  |
| judge  | gemma-3-4b-it (giám khảo chấm eval)    | gemma3:4b                      | 8004 | 6,7  |

Tên phục vụ giữ như tag Ollama nên backend/config.py và các script eval không đổi; chỉ đổi URL bằng biến môi trường
(env_for_backend()).

    python serving/tpu/vllm_servers.py start --python /kaggle/working/vllm-venv/bin/python \\
        --ext DIR --gen DIR --check DIR --judge DIR
    python serving/tpu/vllm_servers.py stop
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

LOG_DIR = os.environ.get("VLLM_LOG_DIR", "/kaggle/working/vllm_logs")
PID_FILE = os.path.join(LOG_DIR, "pids.json")
SERVERS = {
    "ext": dict(name="qwen2.5:7b-instruct", port=8001, chips=[0, 1], max_len=8192),
    "gen": dict(name="qwen-huhu", port=8002, chips=[2, 3], max_len=8192),
    "check": dict(name="gemma3:12b", port=8003, chips=[4, 5], max_len=8192),
    "judge": dict(name="gemma3:4b", port=8004, chips=[6, 7], max_len=8192),
}
# Biến backend/config.py đọc để gọi từng server
BACKEND_ENV = {"ext": ("EXT_BASE_URL",), "gen": ("GEN_BASE_URL",), "check": ("CHECK_BASE_URL",), "judge": ("JUDGE_BASE_URL",)}


def url(key):
    return f"http://localhost:{SERVERS[key]['port']}/v1"


def env_for_backend():
    return {var: url(k) for k, vars_ in BACKEND_ENV.items() for var in vars_}


def tpu_env(chips, port):
    """Cho một process vLLM chỉ thấy các chip được giao (2 chip liền nhau trên topology 2x4 của v5e-8)."""
    return {
        "TPU_VISIBLE_CHIPS": ",".join(map(str, chips)),
        "TPU_CHIPS_PER_PROCESS_BOUNDS": "1,2,1" if len(chips) == 2 else "1,1,1",
        "TPU_PROCESS_BOUNDS": "1,1,1",
        "TPU_PROCESS_PORT": str(port + 100),
        "TPU_PROCESS_ADDRESSES": f"localhost:{port + 100}",
        "CLOUD_TPU_TASK_ID": "0",
    }


def start(python, paths, wait_s):
    os.makedirs(LOG_DIR, exist_ok=True)
    pids = {}
    for key, path in paths.items():
        s = SERVERS[key]
        cmd = [python, "-m", "vllm.entrypoints.openai.api_server", "--model", path, "--served-model-name", s["name"],
               "--port", str(s["port"]), "--tensor-parallel-size", str(len(s["chips"])), "--max-model-len", str(s["max_len"]),
               "--dtype", "bfloat16", "--gpu-memory-utilization", "0.90", "--max-num-seqs", "8",
               # Mặc định lấy tham số sinh của vLLM, không lấy generation_config.json của model (top_p, top_k,
               # repetition_penalty của Qwen); backend tự gửi temperature như khi chạy Ollama
               "--generation-config", "vllm", "--disable-log-requests"]
        if key in ("check", "judge"):
            cmd += ["--limit-mm-per-prompt", json.dumps({"image": 0})]  # Gemma 3 đa phương thức: chỉ dùng văn bản
        log = open(os.path.join(LOG_DIR, f"{key}.log"), "w")
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, **tpu_env(s["chips"], s["port"])},
                             start_new_session=True)
        pids[key] = p.pid
        print(f"[{key}] pid {p.pid} | {s['name']} | chip {s['chips']} | {url(key)} | {path}", flush=True)
    json.dump(pids, open(PID_FILE, "w"))
    deadline = time.time() + wait_s
    pending = set(paths)
    while pending and time.time() < deadline:
        for key in sorted(pending):
            try:
                with urllib.request.urlopen(f"{url(key)}/models", timeout=5) as r:
                    names = [m["id"] for m in json.load(r)["data"]]
                print(f"[{key}] sẵn sàng sau {time.time() - deadline + wait_s:.0f}s: {names}", flush=True)
                pending.discard(key)
            except Exception:
                if not _alive(pids[key]):
                    tail = open(os.path.join(LOG_DIR, f"{key}.log"), encoding="utf-8", errors="replace").read()[-3000:]
                    sys.exit(f"[{key}] vLLM đã thoát. Cuối log:\n{tail}")
        time.sleep(10)
    if pending:
        sys.exit(f"Quá {wait_s}s mà chưa sẵn sàng: {sorted(pending)} (xem {LOG_DIR}/*.log)")


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop():
    if not os.path.exists(PID_FILE):
        return
    for key, pid in json.load(open(PID_FILE)).items():
        try:
            os.killpg(pid, signal.SIGTERM)
            print(f"[{key}] dừng pid {pid}")
        except OSError:
            pass
    os.remove(PID_FILE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["start", "stop"])
    ap.add_argument("--python", default=sys.executable, help="python của môi trường đã cài vllm-tpu")
    for k in SERVERS:
        ap.add_argument(f"--{k}", help=f"thư mục model HF cho server {k}")
    ap.add_argument("--wait", type=int, default=3600, help="giây chờ server sẵn sàng (vLLM biên dịch XLA lúc khởi động)")
    a = ap.parse_args()
    if a.action == "stop":
        stop()
    else:
        paths = {k: getattr(a, k) for k in SERVERS if getattr(a, k)}
        assert paths, "Cần ít nhất một --ext/--gen/--check/--judge"
        start(a.python, paths, a.wait)
