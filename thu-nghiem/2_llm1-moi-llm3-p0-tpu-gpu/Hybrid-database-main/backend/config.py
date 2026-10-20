"""Cấu hình backend, đọc từ biến môi trường / file .env."""
import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# LLM #2 - Generator (model đã fine-tune). Mọi LLM gọi qua API tương thích OpenAI (Ollama, vLLM, ...).
GEN_BASE_URL = os.getenv("GEN_BASE_URL", "http://localhost:11434/v1")
GEN_MODEL = os.getenv("GEN_MODEL", "qwen-huhu")
GEN_API_KEY = os.getenv("GEN_API_KEY", "ollama")
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.3"))   # idea.docx: suy luận temperature ~0.3
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "1024"))
# Model gốc trước fine-tune, chỉ dùng cho baseline (scripts/eval_baselines.py)
BASE_MODEL = os.getenv("BASE_MODEL", "qwen2.5:7b-instruct")

# LLM #1 - Extractor (không fine-tune)
EXT_BASE_URL = os.getenv("EXT_BASE_URL", GEN_BASE_URL)
EXT_MODEL = os.getenv("EXT_MODEL", "qwen2.5:7b-instruct")
EXT_API_KEY = os.getenv("EXT_API_KEY", GEN_API_KEY)
EXT_HISTORY_TURNS = int(os.getenv("EXT_HISTORY_TURNS", "10"))  # số lượt user gần nhất đưa cho LLM #1

# LLM #3 - kiểm tra câu trả lời cuối (thay guardrail tầng 2), khác dòng model với LLM #2 (Qwen) để chấm chéo,
# và khác model giám khảo chấm điểm eval (JUDGE_MODEL) để hệ thống không được lọc bởi chính model chấm nó
CHECK_ENABLED = _bool("CHECK_ENABLED", _bool("GUARDRAIL_L2_ENABLED", True))
CHECK_BASE_URL = os.getenv("CHECK_BASE_URL", EXT_BASE_URL)
CHECK_MODEL = os.getenv("CHECK_MODEL", "gemma3:12b")
CHECK_API_KEY = os.getenv("CHECK_API_KEY", EXT_API_KEY)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))               # idea.docx: retry tối đa 2 lần rồi fallback

# Giám khảo chấm điểm trong các script eval (không nằm trong hệ thống)
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", EXT_BASE_URL)
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemma3:4b")
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY", EXT_API_KEY)


def base_url_for(model):
    """URL server đang phục vụ model (Ollama: một server cho mọi model; vLLM trên TPU: mỗi model một server)."""
    for m, url in ((EXT_MODEL, EXT_BASE_URL), (CHECK_MODEL, CHECK_BASE_URL), (JUDGE_MODEL, JUDGE_BASE_URL)):
        if model == m:
            return url
    return GEN_BASE_URL

LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))

# Truy xuất: "postgres" (SQL + pgvector) hoặc "offline" (đọc file JSON, không cần Docker, không có CBT_CONTEXT)
RETRIEVER = os.getenv("RETRIEVER", "postgres").strip().lower()
NUTRITION_TOP_K = int(os.getenv("NUTRITION_TOP_K", "1"))       # dữ liệu B2 luôn có 1 dòng NUT_ trong context
CBT_ENABLED = _bool("CBT_ENABLED", True)
CBT_MIN_SIMILARITY = float(os.getenv("CBT_MIN_SIMILARITY", "0.0"))

# Phiên hội thoại
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "6"))           # số cặp user/assistant đưa vào prompt LLM #2
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))

# Log từng lượt (để đánh giá / viết báo cáo)
TURN_LOG_PATH = os.getenv("TURN_LOG_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "turns.jsonl"))

# Phản hồi soạn sẵn khi có cờ khủng hoảng. Điền số đường dây nóng đã kiểm chứng vào CRISIS_HOTLINE_TEXT.
CRISIS_HOTLINE_TEXT = os.getenv("CRISIS_HOTLINE_TEXT", "")
