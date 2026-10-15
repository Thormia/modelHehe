"""Hằng số dùng chung, phải giống từng ký tự với dữ liệu fine-tune (idea.docx, traindata_logs/check_traindata.py)."""

FIXED_PROMPT = ("Bạn là chuyên gia tư vấn tâm lý. Luôn phản hồi bằng sự thấu cảm.\nCHỈ gợi ý thực phẩm khi ROUTE_NUTRITION = true, "
                "và CHỈ dùng thực phẩm có trong [NUTRITION_CONTEXT], kèm mã nguồn. Nếu có MISSING_STATES, khéo léo hỏi thêm 1–2 thông tin còn thiếu. Trả về đúng JSON.")

SYSTEM_OVERRIDE = ("[LỆNH ƯU TIÊN CAO NHẤT]:\nHệ thống phát hiện người dùng đang sử dụng thuốc điều trị y tế.\nNhiệm vụ của bạn:\n"
                   "1. Thể hiện sự thấu cảm với tình trạng hiện tại của người dùng.\n"
                   "2. TUYỆT ĐỐI KHÔNG gợi ý bất kỳ loại thực phẩm, thức uống hay dưỡng chất nào để tránh nguy cơ tương tác thuốc.\n"
                   "3. Chuyển hướng an toàn: Khuyên người dùng báo cáo triệu chứng này với bác sĩ đang điều trị trực tiếp.")

# Thứ tự cố định của MISSING_STATES
STATES = ["sleep_state", "appetite_state", "stress_state", "mood_state"]

# Nhãn của từng state. mood_state theo state chart (Figure 2) của Xhani et al. (2026); 3 state còn lại bài báo
# không định nghĩa nhãn nên là bản nháp (idea.docx: "Chốt danh sách nhãn đầy đủ cho sleep_state, appetite_state, stress_state").
STATE_LABELS = {
    "sleep_state": ["Good", "Poor", "Excessive"],
    "appetite_state": ["Normal", "Low", "High"],
    "stress_state": ["Low", "Moderate", "High"],
    "mood_state": ["Calm", "Stressed", "LowMood", "Recovering", "Energized"],
}

OUTPUT_KEYS = {"thought_process", "side_talk", "nutritional_advice", "source_reference"}
THOUGHT_KEYS = {"detected_emotions", "detected_symptoms", "trigger_nutrition", "reasoning"}

# Lời khuyên dinh dưỡng không được có định lượng
MASS_RE = r"\d\s*(mg|mcg|µg|kcal|ml|g)\b"

# Câu GỢI Ý ăn/uống (không phải mọi chữ "ăn uống"): dữ liệu train hỏi "chuyện ăn uống dạo này thế nào?" là hợp lệ,
# nên chỉ bắt mẫu động từ khuyên + món/đồ uống cụ thể.
FOOD_SUGGESTION_RE = (
    r"(nên|hãy|thử|có thể|nhớ|cố gắng|nên dùng|bổ sung)\s+(\S+\s+){0,3}?"
    r"(ăn|uống|húp|dùng|nhâm nhi|bổ sung)\s+(\S+\s+){0,3}?"
    r"(cháo|trà|nước ấm|nước ép|sữa|cà phê|súp|canh|trái cây|hoa quả|rau|hạt|chuối|socola|sô-cô-la|mật ong|"
    r"vitamin|canxi|magie|kẽm|omega|thảo mộc|ngũ cốc|thực phẩm|đồ uống|thức uống|món)"
)
