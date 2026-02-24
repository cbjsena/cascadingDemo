-- SELECT  'DROP TABLE IF EXISTS public."' || tablename || '" CASCADE;' AS drop_sql
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- and tablename not like 'basic%'
--;
DROP TABLE IF EXISTS public.django_migrations CASCADE;
DROP TABLE IF EXISTS public.django_content_type CASCADE;
DROP TABLE IF EXISTS public.auth_permission CASCADE;
DROP TABLE IF EXISTS public.auth_group CASCADE;
DROP TABLE IF EXISTS public.auth_group_permissions CASCADE;
DROP TABLE IF EXISTS public.auth_user_groups CASCADE;
DROP TABLE IF EXISTS public.auth_user_user_permissions CASCADE;
DROP TABLE IF EXISTS public.django_admin_log CASCADE;
DROP TABLE IF EXISTS public.auth_user CASCADE;
DROP TABLE IF EXISTS public.base_bunker_consumption_port CASCADE;
DROP TABLE IF EXISTS public.base_bunker_consumption_sea CASCADE;
DROP TABLE IF EXISTS public.base_bunker_price CASCADE;
DROP TABLE IF EXISTS public.base_cost_canal_fee CASCADE;
DROP TABLE IF EXISTS public.base_vessel_charter_cost CASCADE;
DROP TABLE IF EXISTS public.base_cost_distance CASCADE;
DROP TABLE IF EXISTS public.base_constraint_fixed_schedule_change CASCADE;
DROP TABLE IF EXISTS public.base_constraint_fixed_deployment CASCADE;
DROP TABLE IF EXISTS public.base_schedule_long_range CASCADE;
DROP TABLE IF EXISTS public.base_constraint_port CASCADE;
DROP TABLE IF EXISTS public.base_schedule_proforma CASCADE;
DROP TABLE IF EXISTS public.base_cost_ts_cost CASCADE;
DROP TABLE IF EXISTS public.base_vessel_capacity CASCADE;
DROP TABLE IF EXISTS public.base_vessel_info CASCADE;
DROP TABLE IF EXISTS public.base_week_period CASCADE;
DROP TABLE IF EXISTS public.sce_scenario_info CASCADE;
DROP TABLE IF EXISTS public.sce_proforma_schedule CASCADE;
DROP TABLE IF EXISTS public.sce_cascading_schedule CASCADE;
DROP TABLE IF EXISTS public.sce_proforma_schedule_detail CASCADE;
DROP TABLE IF EXISTS public.sce_constraint_port CASCADE;
DROP TABLE IF EXISTS public.sce_schedule_long_range CASCADE;
DROP TABLE IF EXISTS public.sce_constraint_fixed_deployment CASCADE;
DROP TABLE IF EXISTS public.sce_constraint_fixed_schedule_change CASCADE;
DROP TABLE IF EXISTS public.sce_cost_distance CASCADE;
DROP TABLE IF EXISTS public.sce_vessel_charter_cost CASCADE;
DROP TABLE IF EXISTS public.sce_cascading_schedule_detail CASCADE;
DROP TABLE IF EXISTS public.sce_cost_canal_fee CASCADE;
DROP TABLE IF EXISTS public.sce_bunker_price CASCADE;
DROP TABLE IF EXISTS public.sce_bunker_consumption_sea CASCADE;
DROP TABLE IF EXISTS public.sce_bunker_consumption_port CASCADE;
DROP TABLE IF EXISTS public.sce_cost_ts_cost CASCADE;
DROP TABLE IF EXISTS public.sce_vessel_capacity CASCADE;
DROP TABLE IF EXISTS public.sce_vessel_info CASCADE;
DROP TABLE IF EXISTS public.django_session CASCADE;
