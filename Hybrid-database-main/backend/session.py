"""Lưu phiên hội thoại trên Redis (tự chuyển sang bộ nhớ trong nếu không kết nối được Redis)."""
import json
import os

from .constants import STATES


def new_session():
    return {
        "history": [],                 # lượt assistant chỉ lưu side_talk (idea.docx: lịch sử dựng lại từ side_talk)
        "states": {s: None for s in STATES},
        "medication": False,           # cờ thuốc giữ suốt phiên: đã dùng thuốc thì không bao giờ gợi ý thực phẩm
        "suggested_codes": [],         # mã NUT_ đã gợi ý, tránh lặp món
        "last_suggested_states": None, # states tại lần gợi ý gần nhất
        "turn": 0,
    }


class MemoryStore:
    def __init__(self):
        self._d = {}

    def get(self, sid):
        return json.loads(self._d[sid]) if sid in self._d else new_session()

    def save(self, sid, data):
        self._d[sid] = json.dumps(data, ensure_ascii=False)

    def delete(self, sid):
        self._d.pop(sid, None)


class RedisStore:
    def __init__(self, client, ttl):
        self.r, self.ttl = client, ttl

    def get(self, sid):
        v = self.r.get(f"session:{sid}")
        return json.loads(v) if v else new_session()

    def save(self, sid, data):
        self.r.set(f"session:{sid}", json.dumps(data, ensure_ascii=False), ex=self.ttl)

    def delete(self, sid):
        self.r.delete(f"session:{sid}")


def make_store(ttl):
    try:
        import redis
        client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)),
                             db=0, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return RedisStore(client, ttl)
    except Exception as e:
        print(f"[session] Không kết nối được Redis ({e}); dùng bộ nhớ trong, phiên sẽ mất khi tắt server.")
        return MemoryStore()
