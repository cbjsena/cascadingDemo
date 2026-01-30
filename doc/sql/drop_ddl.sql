SELECT  'DROP TABLE IF EXISTS public."' || tablename || '" CASCADE;' AS drop_sql
FROM pg_tables
WHERE schemaname = 'public'
and tablename not like 'default%'