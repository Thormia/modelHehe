"""Dựng prompt cho LLM #2 đúng định dạng dữ liệu fine-tune (idea.docx: Format dữ liệu chuẩn)."""
import json

from .constants import FIXED_PROMPT, SYSTEM_OVERRIDE


def build_system_prompt(route, missing_states=None, override=False, cbt_context=None, nutrition_context=None):
    """Khối động theo thứ tự cố định; mục không dùng thì bỏ hẳn dòng.

    | Nhánh        | ROUTE | MISSING_STATES | SYSTEM_OVERRIDE | CBT       | NUTRITION |
    | ask_states   | false | không rỗng     | -               | None      | None      |
    | nutrition    | true  | []             | -               | có / None | có        |
    | medication   | false | -              | có              | None      | None      |
    | side_talk    | false | -              | -               | None      | None      |
    """
    assert not (missing_states == [] and not route), "MISSING_STATES: [] không được đi với ROUTE_NUTRITION: false"
    assert not (route and not nutrition_context), "ROUTE_NUTRITION: true cần NUTRITION_CONTEXT"
    lines = [f"[ROUTE_NUTRITION]: {'true' if route else 'false'}"]
    if missing_states is not None:
        lines.append(f"[MISSING_STATES]: {json.dumps(list(missing_states))}")
    if override:
        lines.append(f"[SYSTEM_OVERRIDE]: {SYSTEM_OVERRIDE}")
    lines.append(f"[CBT_CONTEXT]: {cbt_context or 'None'}")
    if nutrition_context:
        lines.append("[NUTRITION_CONTEXT]:\n" + "\n".join(nutrition_context))
    else:
        lines.append("[NUTRITION_CONTEXT]: None")
    return FIXED_PROMPT + "\n\n" + "\n".join(lines)


def build_messages(system_prompt, history, user_message, history_turns=6):
    """Lịch sử: các lượt assistant trước là văn bản thuần (side_talk); chỉ lượt cuối model sinh ra JSON."""
    hist = history[-2 * history_turns:] if history_turns > 0 else []
    while hist and hist[0]["role"] != "user":
        hist = hist[1:]
    return [{"role": "system", "content": system_prompt}] + hist + [{"role": "user", "content": user_message}]
