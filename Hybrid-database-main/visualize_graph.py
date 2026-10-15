import os
import sys
import io
import json

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

base_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(base_dir, "data", "processed", "400 data dinh duong.json")
if not os.path.exists(json_path):
    json_path = os.path.join(base_dir, "data", "processed", "nutrition_data.json")
html_out_path = os.path.join(base_dir, "visualize_graph.html")

def generate_interactive_graph():
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = []
    edges = []
    node_ids = set()

    # Định nghĩa màu sắc cho từng loại node
    COLOR_FOOD = "#FF6B6B"       # Đỏ cam: Thực phẩm
    COLOR_NUTRIENT = "#4ECDC4"   # Xanh ngọc: Vi chất dinh dưỡng
    COLOR_FUNCTION = "#FFE66D"  # Vàng: Đích tác động sinh hóa / Tâm lý

    for item in data:
        food = item.get("food_item", "")
        effect = item.get("ontology_effect", "")
        if not food:
            continue
            
        action = "REGULATES"
        target_func = "general_wellbeing"
        if effect:
            if ":" in effect:
                parts = effect.split(":")
                action = parts[0].strip()
                target_func = parts[1].strip()
            else:
                action = effect.strip()
                target_func = effect.strip()

        # 1. Thêm Node Thực phẩm (Food)
        food_id = f"food_{food}"
        if food_id not in node_ids:
            nodes.append({
                "id": food_id,
                "label": f"🍲 {food}",
                "color": COLOR_FOOD,
                "shape": "dot",
                "size": 24,
                "font": {"size": 15, "color": "#ffffff", "face": "Arial", "strokeWidth": 2, "strokeColor": "#000000"},
                "title": f"<b>Thực phẩm:</b> {food}<br><b>Mô tả:</b> {item.get('content_text', '')}<br><b>Nguồn:</b> {item.get('source_reference', '')}"
            })
            node_ids.add(food_id)

        # 2. Thêm Node Đích tác động (TargetFunction / Triệu chứng)
        if target_func:
            func_id = f"func_{target_func}"
            if func_id not in node_ids:
                nodes.append({
                    "id": func_id,
                    "label": f"🎯 {target_func}",
                    "color": COLOR_FUNCTION,
                    "shape": "box",
                    "size": 20,
                    "font": {"size": 14, "color": "#000000", "face": "Arial", "bold": True},
                    "title": f"<b>Cơ chế / Đích tác động:</b> {target_func}"
                })
                node_ids.add(func_id)

        for nutrient in item.get("key_nutrients", []):
            if nutrient.startswith("("):
                continue
            # 3. Thêm Node Vi chất (Nutrient)
            nutr_id = f"nutr_{nutrient}"
            if nutr_id not in node_ids:
                nodes.append({
                    "id": nutr_id,
                    "label": f"💊 {nutrient}",
                    "color": COLOR_NUTRIENT,
                    "shape": "diamond",
                    "size": 20,
                    "font": {"size": 14, "color": "#111111", "face": "Arial"},
                    "title": f"<b>Vi chất dinh dưỡng:</b> {nutrient}"
                })
                node_ids.add(nutr_id)

            # Cạnh: Food -> CONTAINS -> Nutrient
            edges.append({
                "from": food_id,
                "to": nutr_id,
                "label": "CONTAINS",
                "color": {"color": "#4ECDC4", "opacity": 0.8},
                "arrows": "to",
                "font": {"size": 11, "align": "middle", "color": "#777777"}
            })

            # Cạnh: Nutrient -> HAS_EFFECT -> TargetFunction
            if target_func:
                edges.append({
                    "from": nutr_id,
                    "to": func_id,
                    "label": action,
                    "color": {"color": "#FFE66D", "opacity": 0.8},
                    "arrows": "to",
                    "font": {"size": 11, "align": "middle", "color": "#cc9900"},
                    "dashes": True
                })

        # Hỗ trợ thêm các target_symptoms nếu có
        for symptom in item.get("target_symptoms", []):
            sym_id = f"sym_{symptom}"
            if sym_id not in node_ids:
                nodes.append({
                    "id": sym_id,
                    "label": f"⚠️ {symptom}",
                    "color": "#FF9F43",
                    "shape": "box",
                    "size": 18,
                    "font": {"size": 14, "color": "#000000", "face": "Arial"},
                    "title": f"<b>Triệu chứng:</b> {symptom}"
                })
                node_ids.add(sym_id)
            if target_func:
                edges.append({
                    "from": func_id,
                    "to": sym_id,
                    "label": "TÁC ĐỘNG",
                    "color": {"color": "#FF9F43", "opacity": 0.7},
                    "arrows": "to",
                    "font": {"size": 10, "align": "middle", "color": "#FF9F43"}
                })

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Trực quan hóa Graph RAG - Chatbot Thực Dưỡng Tâm Lý</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1a2e;
            color: #ffffff;
            overflow: hidden;
        }}
        #header {{
            position: absolute;
            top: 15px;
            left: 20px;
            z-index: 100;
            background: rgba(26, 26, 46, 0.85);
            padding: 15px 25px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        h1 {{
            margin: 0 0 5px 0;
            font-size: 20px;
            color: #00d2d3;
        }}
        p {{
            margin: 0;
            font-size: 13px;
            color: #c8d6e5;
        }}
        .legend {{
            margin-top: 10px;
            display: flex;
            gap: 15px;
            font-size: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .legend-dot {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            display: inline-block;
        }}
        #network {{
            width: 100vw;
            height: 100vh;
        }}
        #instruction {{
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.7);
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 12px;
            color: #8395a7;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>🌿 Sơ Đồ Đồ Thị Tri Thức Graph RAG (Ontology Network)</h1>
        <p>Biểu diễn quan hệ nhân quả: <b>Thực phẩm tự nhiên ➔ Vi chất ➔ Triệu chứng thể chất</b></p>
        <div class="legend">
            <div class="legend-item"><span class="legend-dot" style="background: {COLOR_FOOD};"></span> Thực phẩm (Food)</div>
            <div class="legend-item"><span class="legend-dot" style="background: {COLOR_NUTRIENT};"></span> Vi chất dinh dưỡng (Nutrient)</div>
            <div class="legend-item"><span class="legend-dot" style="background: {COLOR_FUNCTION};"></span> Đích tác động sinh hóa / Tâm lý (Target Function)</div>
        </div>
    </div>

    <div id="network"></div>
    <div id="instruction">💡 <i>Kéo chuột để di chuyển, cuộn để phóng to/thu nhỏ, click vào node để xem chi tiết.</i></div>

    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
        var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});

        var container = document.getElementById('network');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                width: 1.5,
                shadow: true,
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                stabilization: false,
                barnesHut: {{
                    gravitationalConstant: -3000,
                    springConstant: 0.04,
                    springLength: 120
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100
            }}
        }};

        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>
"""

    with open(html_out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Đã tạo thành công file trực quan hóa đồ thị tương tác tại: {html_out_path}")

if __name__ == "__main__":
    generate_interactive_graph()
