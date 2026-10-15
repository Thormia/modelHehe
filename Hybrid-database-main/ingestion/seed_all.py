import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Thêm đường dẫn gốc vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.ingest_postgres import run_postgres_ingestion
from ingestion.ingest_neo4j import run_neo4j_ingestion

def main():
    print("================================================================")
    print("      KHỞI TẠO VÀ NẠP DỮ LIỆU VÀO HYBRID DATABASE (POSTGRES + NEO4J)")
    print("================================================================")
    
    try:
        print("\n--- BƯỚC 1: NẠP DỮ LIỆU POSTGRESQL & PGVECTOR ---")
        run_postgres_ingestion()
    except Exception as e:
        print(f"[LỖI POSTGRESQL] Không thể nạp dữ liệu: {e}")
        print(">> Hãy đảm bảo Docker PostgreSQL đang chạy (docker-compose up -d)")

    try:
        print("\n--- BƯỚC 2: NẠP DỮ LIỆU ĐỒ THỊ TRI THỨC NEO4J ---")
        run_neo4j_ingestion()
    except Exception as e:
        print(f"[LỖI NEO4J] Không thể nạp dữ liệu: {e}")
        print(">> Hãy đảm bảo Docker Neo4j đang chạy (docker-compose up -d)")

    print("\n================================================================")
    print(">>> HOÀN TẤT TẤT CẢ CÔNG ĐOẠN SEED HYBRID DATABASE!")
    print("================================================================")

if __name__ == "__main__":
    main()
