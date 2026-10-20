"""Gộp LoRA fine-tune vào trọng số Qwen2.5-7B-Instruct (bf16) để vLLM trên TPU phục vụ như một model thường.

Cùng công thức với notebook export_gguf_kaggle (W = W + (B @ A) * lora_alpha / r), nhưng giữ bf16, không lượng tử
GGUF Q4_K_M như bản chạy bằng Ollama.

    python serving/tpu/merge_lora.py --base DIR_QWEN_GỐC --adapter DIR_best_adapter --out DIR_RA
"""
import argparse
import glob
import json
import os
import shutil

from safetensors import safe_open
from safetensors.torch import load_file, save_file


def merge(base, adapter, out):
    cfg = json.load(open(os.path.join(adapter, "adapter_config.json")))
    assert not cfg.get("use_rslora") and not cfg.get("use_dora") and not cfg.get("fan_in_fan_out")
    scale = cfg["lora_alpha"] / cfg["r"]
    ad = os.path.join(adapter, "adapter_model.safetensors")
    pairs = {}  # tên tensor gốc -> (khóa lora_A, khóa lora_B)
    with safe_open(ad, "pt") as f:
        for k in f.keys():
            if k.endswith(".lora_A.weight"):
                pairs[k.replace("base_model.model.", "", 1).replace(".lora_A.weight", ".weight")] = (k, k.replace("lora_A", "lora_B"))
    print(f"Adapter: {adapter} | {len(pairs)} ma trận LoRA | scale = {scale}", flush=True)
    os.makedirs(out, exist_ok=True)
    merged = set()
    with safe_open(ad, "pt") as lora:
        for shard in sorted(glob.glob(os.path.join(base, "*.safetensors"))):
            t = load_file(shard)
            for name in t:
                if name in pairs:
                    a, b = pairs[name]
                    A, B = lora.get_tensor(a).float(), lora.get_tensor(b).float()
                    t[name] = (t[name].float() + (B @ A) * scale).to(t[name].dtype)
                    merged.add(name)
            save_file(t, os.path.join(out, os.path.basename(shard)), metadata={"format": "pt"})
            print("  xong", os.path.basename(shard), flush=True)
            del t
    assert merged == set(pairs), f"Thiếu: {sorted(set(pairs) - merged)[:5]}"
    for fn in os.listdir(base):
        if not fn.endswith(".safetensors") and os.path.isfile(os.path.join(base, fn)):
            shutil.copy(os.path.join(base, fn), out)
    print("Đã gộp", len(merged), "ma trận ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    merge(a.base, a.adapter, a.out)
