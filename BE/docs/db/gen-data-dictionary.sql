-- =============================================================================
-- 데이터 사전 생성기 (S15P11A108-52)
--
-- schema.sql + comments.sql 이 적용된 DB 에서 실제 메타데이터를 읽어
-- data-dictionary.md 본문을 만든다. 손으로 옮겨 적지 않는 이유는
-- 스키마가 바뀌면 문서가 조용히 어긋나기 때문이다.
--
-- 실행 (레포 루트 기준, 결과는 stdout):
--   docker exec -i vintib-postgres psql -U postgres -q -d schema_check -t -A -f - < BE/docs/db/gen-data-dictionary.sql
--
-- 전체 재생성은 BE/docs/db/regen.sh 참고.
-- =============================================================================

WITH cols AS (
    SELECT
        c.oid                                            AS reloid,
        c.relname                                        AS table_name,
        a.attnum,
        a.attname                                        AS column_name,
        -- 타입 표기를 짧게: character varying(n) → varchar(n), timestamp with time zone → timestamptz
        replace(
            replace(format_type(a.atttypid, a.atttypmod), 'character varying', 'varchar'),
            'timestamp with time zone', 'timestamptz')   AS data_type,
        a.attnotnull                                     AS not_null,
        -- 기본값에서 타입 캐스트 노이즈를 걷어낸다: 'READY'::character varying → 'READY'
        replace(
            replace(pg_get_expr(d.adbin, d.adrelid), '::character varying', ''),
            '::text', '')                                AS default_expr,
        col_description(c.oid, a.attnum)                 AS col_comment
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_attribute a ON a.attrelid = c.oid
    LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND a.attnum > 0
      AND NOT a.attisdropped
),
-- 컬럼별 키 표기: PK / FK→대상 / UQ
col_keys AS (
    SELECT
        con.conrelid AS reloid,
        k.attnum,
        string_agg(DISTINCT
            CASE con.contype
                WHEN 'p' THEN 'PK'
                WHEN 'f' THEN 'FK→' || tf.relname
                WHEN 'u' THEN 'UQ'
            END, ', ' ORDER BY
            CASE con.contype
                WHEN 'p' THEN 'PK'
                WHEN 'f' THEN 'FK→' || tf.relname
                WHEN 'u' THEN 'UQ'
            END) AS keys
    FROM pg_constraint con
    CROSS JOIN LATERAL unnest(con.conkey) AS k(attnum)
    LEFT JOIN pg_class tf ON tf.oid = con.confrelid
    WHERE con.contype IN ('p', 'f', 'u')
    GROUP BY con.conrelid, k.attnum
),
-- 테이블별 CHECK 제약 (NOT NULL 자동 생성분 제외)
table_checks AS (
    SELECT
        con.conrelid AS reloid,
        string_agg('- `' || con.conname || '` — `' ||
                   replace(pg_get_constraintdef(con.oid), '|', '\|') || '`',
                   E'\n' ORDER BY con.conname) AS checks
    FROM pg_constraint con
    WHERE con.contype = 'c'
    GROUP BY con.conrelid
),
-- 테이블별 인덱스 (PK 인덱스 제외). 부분 유니크 인덱스가 정책의 핵심이라 정의를 그대로 싣는다.
table_indexes AS (
    SELECT
        i.indrelid AS reloid,
        string_agg('- `' || ic.relname || '` — `' ||
                   replace(pg_get_indexdef(i.indexrelid), '|', '\|') || '`',
                   E'\n' ORDER BY ic.relname) AS indexes
    FROM pg_index i
    JOIN pg_class ic ON ic.oid = i.indexrelid
    WHERE NOT i.indisprimary
    GROUP BY i.indrelid
),
-- 컬럼 표
col_rows AS (
    SELECT
        c.reloid,
        c.table_name,
        string_agg(
            '| `' || c.column_name || '` | `' || c.data_type || '` | ' ||
            CASE WHEN c.not_null THEN 'NOT NULL' ELSE '' END || ' | ' ||
            COALESCE('`' || replace(c.default_expr, '|', '\|') || '`', '') || ' | ' ||
            COALESCE(k.keys, '') || ' | ' ||
            COALESCE(replace(c.col_comment, '|', '\|'), '') || ' |',
            E'\n' ORDER BY c.attnum) AS body
    FROM cols c
    LEFT JOIN col_keys k ON k.reloid = c.reloid AND k.attnum = c.attnum
    GROUP BY c.reloid, c.table_name
)
SELECT string_agg(
    '### `' || r.table_name || '`' || E'\n\n' ||
    COALESCE(obj_description(r.reloid) || E'\n\n', '') ||
    '| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |' || E'\n' ||
    '| --- | --- | --- | --- | --- | --- |' || E'\n' ||
    r.body || E'\n' ||
    COALESCE(E'\n**CHECK 제약**\n\n' || tc.checks || E'\n', '') ||
    COALESCE(E'\n**인덱스**\n\n' || ti.indexes || E'\n', ''),
    E'\n---\n\n' ORDER BY r.table_name)
FROM col_rows r
LEFT JOIN table_checks  tc ON tc.reloid = r.reloid
LEFT JOIN table_indexes ti ON ti.reloid = r.reloid;
