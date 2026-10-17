"""Bộ từ khóa an toàn, chạy song song với LLM #1 (idea.docx: phần An toàn).

Từ khóa khủng hoảng chỉ gồm cụm rõ nghĩa; các cách nói mơ hồ ("mệt chết đi được", "muốn chết vì xấu hổ")
để LLM #1 quyết định, tránh trả phản hồi khủng hoảng cho câu nói quá.
"""
import re
from dataclasses import dataclass

from . import config

CRISIS_RE = re.compile(
    r"(tự tử|tự sát|tự hại|tự làm hại|rạch tay|cắt tay|không muốn sống|chán sống|kết liễu|kết thúc cuộc đời|"
    r"kết thúc cuộc sống|nhẹ nợ|rảnh nợ|đi cho xong|biến mất cho|không muốn tỉnh dậy|chết quách|"
    r"nhảy cầu|nhảy lầu|treo cổ|uống thuốc ngủ cho)", re.I)

# Keyword chỉ bắt từ khoá thuốc điều trị ("thuốc lá" không khớp ở tầng này); các tình huống cơ thể khác thường
# của nhóm B3 (mang thai, ốm, vừa mổ, chất kích thích...) do LLM #1 nhận diện qua medication_alert.
# "tiêm kích trứng", "đợt điều trị" dễ bị bỏ sót nên liệt kê riêng
MEDICATION_RE = re.compile(
    r"(thuốc(?!\s*lá)|tiêm|kích trứng|liều|kê đơn|đơn thuốc|hóa trị|hoá trị|xạ trị|nội tiết|hormone|hoóc[- ]?môn|"
    r"insulin|đợt điều trị|đang điều trị|phác đồ|chạy thận)", re.I)


@dataclass
class KeywordResult:
    crisis: bool
    medication: bool
    crisis_match: str = ""
    medication_match: str = ""


def scan(text):
    c = CRISIS_RE.search(text or "")
    m = MEDICATION_RE.search(text or "")
    return KeywordResult(bool(c), bool(m), c.group(0) if c else "", m.group(0) if m else "")


def crisis_response(panic=False):
    """panic=True khi đồng thời có cờ hoảng loạn: thêm hướng dẫn ổn định nhịp thở, giữ nguyên phần an toàn."""
    hotline = f" {config.CRISIS_HOTLINE_TEXT.strip()}" if config.CRISIS_HOTLINE_TEXT.strip() else ""
    grounding = ("Nếu bạn đang hoảng loạn, hãy ngồi xuống ở chỗ an toàn và thử thở chậm cùng mình: hít vào đếm đến 4, "
                 "giữ 2 nhịp, thở ra đếm đến 6, lặp lại vài lần. ") if panic else ""
    return ("Mình rất tiếc khi bạn đang phải mang trong lòng điều nặng nề như vậy, và cảm ơn bạn đã tin tưởng nói ra. "
            f"Sự an toàn của bạn lúc này là điều quan trọng nhất. {grounding}Nếu bạn đang nghĩ tới việc làm hại bản thân hoặc cảm thấy "
            "không an toàn, hãy gọi ngay 115 hoặc đến cơ sở y tế gần nhất, và báo cho một người thân hay bạn bè ở gần "
            f"để họ có thể ở bên bạn.{hotline} Bạn không phải một mình vượt qua chuyện này. "
            "Bạn có thể cho mình biết hiện tại bạn có đang ở nơi an toàn không?")


def panic_response():
    """Cơn hoảng loạn / lo âu cấp tính đang diễn ra (panic_flag của LLM #1, không có từ khóa riêng: người dùng
    thường kể lại cơn hoảng loạn đã qua, những câu đó cần được trò chuyện bình thường)."""
    hotline = f" {config.CRISIS_HOTLINE_TEXT.strip()}" if config.CRISIS_HOTLINE_TEXT.strip() else ""
    return ("Mình đang ở đây với bạn. Cảm giác lúc này rất đáng sợ, nhưng cơn hoảng loạn thường sẽ dịu dần sau vài phút. "
            "Nếu được, bạn hãy dừng việc đang làm và ngồi xuống ở chỗ an toàn (nếu đang lái xe, hãy tấp vào lề trước). "
            "Thử thở chậm cùng mình: hít vào bằng mũi đếm đến 4, giữ 2 nhịp, thở ra bằng miệng đếm đến 6, lặp lại vài lần. "
            "Sau đó nhìn quanh và gọi tên 5 thứ bạn đang thấy để kéo mình về hiện tại. "
            "Nếu bạn bị đau hoặc tức ngực, khó thở mãi không đỡ, sắp ngất, hoặc đang gặp nguy hiểm, hãy gọi ngay 115 "
            "(hoặc 113 nếu bị tấn công, bạo lực) hay nhờ người ở gần giúp đỡ."
            f"{hotline} Bạn đang ở đâu, và có ai ở gần bạn lúc này không?")
