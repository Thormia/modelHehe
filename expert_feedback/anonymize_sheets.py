"""Tạo bản ẩn danh của phiếu chấm chuyên gia để đưa lên GitHub (bản gốc có họ tên, bị .gitignore).

    python expert_feedback/anonymize_sheets.py      (từ thư mục C:/FPT/AIM)  ->  expert_feedback/anonymized/*.xlsx

Xoá họ tên (ô A5/B5 sheet 0_HuongDan), bỏ tên cơ sở đào tạo trong ô chuyên môn, xoá metadata tác giả
của file. Điểm, cột chọn và nhận xét ở các sheet 1–4 giữ nguyên.
"""
import glob
import os
import re

import openpyxl

SRC = "expert_feedback"
DST = os.path.join(SRC, "anonymized")


def main():
    os.makedirs(DST, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(SRC, "expert_review_sheet_*.xlsx"))):
        wb = openpyxl.load_workbook(f, data_only=True)  # giữ giá trị đã tính của ô công thức
        ws = wb["0_HuongDan"]
        ws["A5"] = "Họ tên chuyên gia: (đã ẩn)"
        ws["B5"] = None
        for cell in ("A6", "B6"):
            v = ws[cell].value
            if isinstance(v, str) and re.search(r"(?i)trường|đại học|bệnh viện", v):
                ws[cell] = "Sinh viên Y dược" if re.search(r"(?i)y dược", v) else (re.sub(r"(?i)\s*trường\s.*$", "", v).strip() or "Sinh viên")
        wb.properties.creator = None
        wb.properties.lastModifiedBy = None
        wb.save(os.path.join(DST, os.path.basename(f)))
        print(os.path.basename(f))


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
