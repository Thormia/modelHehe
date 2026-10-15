// ====================================================================
// LƯỢC ĐỒ RÀNG BUỘC CHO ĐỒ THỊ TRI THỨC NEO4J (GRAPH RAG)
// ====================================================================

CREATE CONSTRAINT unique_symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT unique_nutrient_name IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT unique_food_name IF NOT EXISTS FOR (f:Food) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT unique_mental_state IF NOT EXISTS FOR (m:MentalState) REQUIRE m.name IS UNIQUE;
