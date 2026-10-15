#!/usr/bin/env bash
# Dựng toàn bộ hạ tầng của hệ thống trên Kaggle (không có Docker), cùng phiên bản với docker-compose.yml:
#   PostgreSQL 16 + pgvector, Redis, Neo4j 5.18 community, Ollama (cùng bản với máy local).
# Chạy với quyền root trong notebook Kaggle (bật Internet):  bash serving/kaggle_services.sh
set -euo pipefail

OLLAMA_VERSION="${OLLAMA_VERSION:-0.40.3}"
NEO4J_VERSION="${NEO4J_VERSION:-5.18.0}"
PG_USER="${POSTGRES_USER:-admin}"
PG_PASS="${POSTGRES_PASSWORD:-password123}"
PG_DB="${POSTGRES_DB:-mental_nutrition_db}"
NEO4J_PASS="${NEO4J_PASSWORD:-password123}"
export DEBIAN_FRONTEND=noninteractive

echo "=== apt: PostgreSQL 16 + pgvector (kho PGDG), Redis, Java 17 cho Neo4j"
if ! dpkg -s postgresql-16-pgvector redis-server openjdk-17-jre-headless > /dev/null 2>&1; then
apt-get update -qq
apt-get install -y -qq curl ca-certificates gnupg lsb-release zstd > /dev/null
install -d /usr/share/postgresql-common/pgdg
curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list
apt-get update -qq
apt-get install -y -qq postgresql-16 postgresql-16-pgvector redis-server openjdk-17-jre-headless > /dev/null
fi

echo "=== PostgreSQL"
pg_isready -q -h localhost -p 5432 || pg_ctlcluster 16 main start || service postgresql start
until pg_isready -q -h localhost -p 5432; do sleep 1; done
su postgres -c "psql -v ON_ERROR_STOP=1 -q" <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${PG_USER}') THEN
    CREATE ROLE ${PG_USER} LOGIN SUPERUSER PASSWORD '${PG_PASS}';
  END IF;
END \$\$;
SQL
su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${PG_DB}'\"" | grep -q 1 \
  || su postgres -c "createdb -O ${PG_USER} ${PG_DB}"
su postgres -c "psql -q -d ${PG_DB} -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
psql --version; su postgres -c "psql -tAc \"SELECT 'pgvector ' || extversion FROM pg_extension WHERE extname='vector'\" ${PG_DB}"

echo "=== Redis"
redis-cli ping > /dev/null 2>&1 || redis-server --daemonize yes --port 6379 > /dev/null
until redis-cli ping > /dev/null 2>&1; do sleep 1; done
redis-server --version

echo "=== Neo4j ${NEO4J_VERSION} community"
if [ ! -d /opt/neo4j ]; then
  curl -fsSL -o /tmp/neo4j.tar.gz "https://dist.neo4j.org/neo4j-community-${NEO4J_VERSION}-unix.tar.gz"
  tar -xzf /tmp/neo4j.tar.gz -C /opt && mv "/opt/neo4j-community-${NEO4J_VERSION}" /opt/neo4j
  /opt/neo4j/bin/neo4j-admin dbms set-initial-password "${NEO4J_PASS}"
fi
/opt/neo4j/bin/neo4j status > /dev/null 2>&1 || /opt/neo4j/bin/neo4j start > /dev/null
until curl -s -o /dev/null http://localhost:7474; do sleep 2; done
echo "neo4j ${NEO4J_VERSION} đang chạy"

echo "=== Ollama ${OLLAMA_VERSION}"
if ! command -v ollama > /dev/null || ! ollama --version 2>/dev/null | grep -q "${OLLAMA_VERSION}"; then
  curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION="${OLLAMA_VERSION}" sh > /dev/null
fi
# 2 x T4 (32 GB): giữ cả 3 model trên GPU cùng lúc, không nạp luân phiên như máy 6 GB
# Luôn khởi động lại để chắc chắn server chạy với các biến trên (install.sh có thể đã tự bật server mặc định)
pkill -f "ollama serve" || true
sleep 2
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=2 OLLAMA_KEEP_ALIVE=-1 nohup ollama serve > /kaggle/working/ollama.log 2>&1 &
until curl -s http://localhost:11434/api/version > /dev/null; do sleep 1; done
curl -s http://localhost:11434/api/version; echo
