"""Kiểm tra cờ y tế (B3) của LLM #1 trên câu tự viết (tập dev, KHÔNG lấy từ bộ test hay tập test fine-tune).

Quy tắc của nhóm: thuốc, bệnh, mang thai, mổ, kỳ kinh, vaccine, xăm là B3; rượu bia, thuốc lá/vape, cà phê, nhịn ăn,
thức trắng chỉ là B3 khi đã gây thay đổi trên cơ thể (triệu chứng thể chất).

    python scripts/dev_b3_check.py
"""
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import config  # noqa: E402
from backend.extractor import Extractor  # noqa: E402
from backend.llm import LLMClient  # noqa: E402

# (câu, health_alert mong đợi)
DEV = [
    ("Mấy hôm nay chạy dự án mình gần như không ngủ, sáng nay đứng dậy thì chóng mặt suýt ngã.", True),
    ("Mình uống ba ly cà phê để tỉnh, giờ tim cứ đập thình thịch, người vã mồ hôi.", True),
    ("Tối qua nhậu với đồng nghiệp, sáng nay đầu nhức như búa bổ, buồn nôn mãi.", True),
    ("Mình bỏ bữa cả ngày vì bận, giờ người run rẩy, mắt hoa lên.", True),
    ("Đang cai thuốc lá được một tuần, tay chân cứ bủn rủn, đầu nhức.", True),
    ("Thức suốt hai đêm ôn thi, giờ mắt nhìn mờ hẳn đi, đầu đau.", True),
    ("Mẹ mình đang mang thai tháng thứ 4, dạo này mẹ hay buồn, mình nên làm gì?", True),
    ("Mình đang uống kháng sinh vì viêm họng.", True),
    ("Mình nghiện cà phê, ngày nào cũng ba ly.", False),
    ("Cuối tuần mình hay đi nhậu với bạn cho vui.", False),
    ("Dạo này mình hay thức khuya xem phim, hôm sau hơi buồn ngủ.", False),
    ("Mình đang nhịn ăn tối để giảm cân, vẫn thấy bình thường.", False),
    ("Mình vape lâu rồi, giờ muốn bỏ mà khó quá.", False),
    ("Áp lực công việc làm mình mất ngủ, hay cáu gắt.", False),
    ("Mình buồn vì chia tay, chẳng muốn ăn gì.", False),
    ("Thi xong rồi mà mình vẫn lo, ngủ chập chờn mấy hôm nay.", False),
]


def main():
    ext = Extractor(LLMClient(config.EXT_BASE_URL, config.EXT_MODEL, config.EXT_API_KEY, config.LLM_TIMEOUT))
    ok = 0
    for text, want in DEV:
        e = ext.extract([{"role": "user", "content": text}])
        good = e.ok and e.medication_alert == want
        ok += good
        print(f"{'OK ' if good else 'SAI'} mong đợi={want!s:5} được={e.medication_alert!s:5} crisis={e.crisis_flag!s:5} | {text}", flush=True)
    print(f"\n{ok}/{len(DEV)} đúng")


if __name__ == "__main__":
    main()
