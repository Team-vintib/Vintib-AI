# DB 설계 산출물

빈티지 라이브 경매 플랫폼의 DB 설계 문서. 대상은 **PostgreSQL 18**이다.

## 무엇부터 읽나

| 목적 | 문서 |
| --- | --- |
| 구조와 **설계 이유**를 알고 싶다 | [`erd.md`](./erd.md) — ERD, 상태 전이, 정책→제약 매핑, 미확인 가정 |
| 컬럼 하나의 타입·제약을 찾고 싶다 | [`data-dictionary.md`](./data-dictionary.md) — 테이블 25개 전체 |
| 테이블을 직접 만들어 보고 싶다 | [`schema.sql`](./schema.sql) |
| 카테고리 id가 실제로 뭘 가리키는지 찾고 싶다 | [`category-taxonomy.md`](./category-taxonomy.md) — 성별·대분류·소분류 111개 시드 값 |

## 파일 구성

```
BE/docs/db/
├── schema.sql                   ← 스키마 원본 (단일 기준)
├── comments.sql                 ← 컬럼 설명 (COMMENT ON)
├── constraint-test.sql          ← 정책 위반이 거부되는지 검증
├── gen-data-dictionary.sql      ← 데이터 사전 생성 쿼리
├── data-dictionary.header.md    ← 데이터 사전 머리말 (수동 작성)
├── data-dictionary.md           ← 🤖 자동 생성 — 직접 고치지 말 것
├── category-taxonomy.md         ← 카테고리 시드 값 정리 (수동 작성, seed.sql 바뀌면 같이 갱신)
├── erd.md                       ← ERD·상태 설계 (mermaid 원본)
├── img/                         ← 🤖 자동 생성 — erd.md 에서 뽑은 SVG·PNG
├── regen.sh                     ← 데이터 사전 재생성
└── export-erd.sh                ← ERD 이미지 재생성
```

## 수정할 때

전제: `docker compose up -d`로 `vintib-postgres`가 떠 있어야 한다.

**스키마를 바꿨다면** — `schema.sql` 수정 후 검증하고 문서를 다시 뽑는다.

```bash
bash BE/docs/db/regen.sh
```

**설명 문구만 바꾸고 싶다면** — `comments.sql`을 고치고 위 명령을 다시 돌린다. `data-dictionary.md`를 직접 고치면 다음 재생성 때 사라진다.

**다이어그램을 바꿨다면** — `erd.md`의 mermaid 블록을 고치고 이미지를 다시 뽑는다.

```bash
bash BE/docs/db/export-erd.sh
```

**제약이 의도대로 동작하는지 확인하려면**

```bash
docker exec -i vintib-postgres psql -U postgres -c "DROP DATABASE IF EXISTS schema_check;" -c "CREATE DATABASE schema_check;"
docker exec -i vintib-postgres psql -U postgres -d schema_check -v ON_ERROR_STOP=1 -f - < BE/docs/db/schema.sql
docker exec -i vintib-postgres psql -U postgres -d schema_check -f - < BE/docs/db/constraint-test.sql
```

기대 결과는 **통과 11 / 실패 0**이다.

## 왜 문서를 생성하나

데이터 사전을 손으로 옮겨 적으면 스키마가 바뀔 때 **조용히 어긋난다.** 컬럼이 하나 늘어도 문서는 그대로고, 어긋난 걸 알아채는 시점은 보통 그 문서를 믿고 코드를 짠 뒤다.

구조는 실제 DB의 시스템 카탈로그에서 읽고 설명은 `COMMENT ON`으로 DB에 심어 함께 읽는다. 그래서 문서와 DDL이 갈라질 수 없다. 부수 효과로 `psql \d+`·DataGrip·DBeaver에서도 같은 설명이 보인다.
