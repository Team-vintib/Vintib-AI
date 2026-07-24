#!/usr/bin/env bash
# 데이터 사전 재생성 (S15P11A108-52)
#
# schema.sql 이 바뀌면 이 스크립트를 돌려 data-dictionary.md 를 다시 만든다.
# 문서를 손으로 고치지 말 것 — 다음 재생성 때 덮어써진다.
# 설명 문구를 바꾸려면 comments.sql 을 수정한다.
#
# 사용법 (레포 루트에서): bash BE/docs/db/regen.sh
# 전제: docker compose up -d 로 vintib-postgres 가 떠 있어야 한다.

set -euo pipefail

DB=schema_check
PG=vintib-postgres
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$DIR/data-dictionary.md"

if ! docker ps --format '{{.Names}}' | grep -qx "$PG"; then
    echo "오류: $PG 컨테이너가 떠 있지 않습니다. 'docker compose up -d' 를 먼저 실행하세요." >&2
    exit 1
fi

echo "1/4 검증용 DB 재생성"
docker exec -i "$PG" psql -U postgres -q \
    -c "DROP DATABASE IF EXISTS $DB;" -c "CREATE DATABASE $DB;"

echo "2/4 schema.sql 적용"
docker exec -i "$PG" psql -U postgres -q -d "$DB" -v ON_ERROR_STOP=1 -f - < "$DIR/schema.sql"

echo "3/4 comments.sql 적용"
docker exec -i "$PG" psql -U postgres -q -d "$DB" -v ON_ERROR_STOP=1 -f - < "$DIR/comments.sql"

echo "4/4 data-dictionary.md 생성"
{
    cat "$DIR/data-dictionary.header.md"
    echo
    docker exec -i "$PG" psql -U postgres -q -d "$DB" -t -A -v ON_ERROR_STOP=1 \
        -f - < "$DIR/gen-data-dictionary.sql"
} > "$OUT"

docker exec -i "$PG" psql -U postgres -q -c "DROP DATABASE $DB;"

echo "완료: $OUT ($(wc -l < "$OUT") 줄)"
