-- ====================================================================
-- LƯỢC ĐỒ CƠ SỞ DỮ LIỆU HYBRID DATABASE (POSTGRESQL + PGVECTOR)
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Bảng Dinh dưỡng Thực phẩm (Tra cứu SQL - 400 data dinh duong.json)
CREATE TABLE IF NOT EXISTS nutrition_support (
    id SERIAL PRIMARY KEY,
    food_item VARCHAR(255) NOT NULL,
    key_nutrients TEXT[] NOT NULL,
    ontology_effect VARCHAR(255),
    content_text TEXT,
    source_reference VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nutrition_food ON nutrition_support (food_item);
CREATE INDEX IF NOT EXISTS idx_nutrition_nutrients ON nutrition_support USING GIN (key_nutrients);
CREATE INDEX IF NOT EXISTS idx_nutrition_ontology ON nutrition_support (ontology_effect);

-- 2. Bảng Tri thức Tâm lý & Cơ chế Thần kinh (Tra cứu Vector - psychology_dataset_vi.json)
CREATE TABLE IF NOT EXISTS psychology_knowledge (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(100) UNIQUE NOT NULL,
    target_mental_state VARCHAR(150),
    tags TEXT[],
    content_text TEXT NOT NULL,
    source_reference VARCHAR(255) NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_psychology_embedding ON psychology_knowledge
USING hnsw (embedding vector_cosine_ops);

-- 3. Mã nguồn NUT_xxx (thứ tự 1-based trong file 400 thực phẩm, giống dữ liệu fine-tune) và cờ loại khỏi gợi ý
ALTER TABLE nutrition_support ADD COLUMN IF NOT EXISTS nut_code VARCHAR(16);
ALTER TABLE nutrition_support ADD COLUMN IF NOT EXISTS excluded BOOLEAN NOT NULL DEFAULT FALSE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_nutrition_code ON nutrition_support (nut_code);

-- 4. Ánh xạ state -> đích tác động (state_effect_map.json); state_name = '*' là mặc định
CREATE TABLE IF NOT EXISTS state_effect_map (
    state_name VARCHAR(32) NOT NULL,
    state_value VARCHAR(32) NOT NULL,
    target_function VARCHAR(64) NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (state_name, state_value, target_function)
);

-- 5. Danh mục kỹ thuật CBT / chánh niệm cho [CBT_CONTEXT] (cbt_catalog.json), embedding lấy từ psychology_knowledge
CREATE TABLE IF NOT EXISTS cbt_catalog (
    chunk_id VARCHAR(100) PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL
);
