# PostgreSQL 전용 테이블 정의서 생성 쿼리
# Django raw query 실행 시 % 문자는 %%로 이스케이프해야 함
TABLE_DEF_QUERY_POSTGRESQL = """
SELECT
    c.table_name      AS table_name,
    c.column_name     AS column_name,
    c.data_type       AS data_type,
    c.is_nullable     AS nullable,
    pgd.description   AS comment
FROM information_schema.columns c
LEFT JOIN pg_catalog.pg_statio_all_tables st
       ON c.table_schema = st.schemaname
      AND c.table_name   = st.relname
LEFT JOIN pg_catalog.pg_description pgd
       ON pgd.objoid = st.relid
      AND pgd.objsubid = c.ordinal_position
WHERE c.table_schema = 'public'
  AND c.table_name  LIKE 'base%%'  -- Django raw query에서 %는 %%로 이스케이프 필요
  AND c.column_name != 'id'
ORDER BY c.table_name, c.ordinal_position;
"""
