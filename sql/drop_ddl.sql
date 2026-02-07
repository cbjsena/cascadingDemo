SELECT  'DROP TABLE IF EXISTS public."' || tablename || '" CASCADE;' AS drop_sql
FROM pg_tables
WHERE schemaname = 'public'
and tablename not like 'default%'
;
DROP TABLE IF EXISTS public."django_migrations" CASCADE;
DROP TABLE IF EXISTS public."django_content_type" CASCADE;
DROP TABLE IF EXISTS public."auth_permission" CASCADE;
DROP TABLE IF EXISTS public."auth_group" CASCADE;
DROP TABLE IF EXISTS public."auth_group_permissions" CASCADE;
DROP TABLE IF EXISTS public."auth_user" CASCADE;
DROP TABLE IF EXISTS public."auth_user_groups" CASCADE;
DROP TABLE IF EXISTS public."auth_user_user_permissions" CASCADE;
DROP TABLE IF EXISTS public."django_admin_log" CASCADE;
DROP TABLE IF EXISTS public."cas_input_data_snapshot" CASCADE;
DROP TABLE IF EXISTS public."cas_fuel_eu_ghg_target" CASCADE;
DROP TABLE IF EXISTS public."cas_fuel_eu_bunker" CASCADE;
DROP TABLE IF EXISTS public."cas_fuel_eu" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_exchange_rate" CASCADE;
DROP TABLE IF EXISTS public."cas_ets_ts_port" CASCADE;
DROP TABLE IF EXISTS public."cas_ets_eua" CASCADE;
DROP TABLE IF EXISTS public."cas_ets_country" CASCADE;
DROP TABLE IF EXISTS public."cas_ets_bunker_consumption" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_distance" CASCADE;
DROP TABLE IF EXISTS public."cas_vessel_charter_cost" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_canal_fee" CASCADE;
DROP TABLE IF EXISTS public."cas_bunker_bunker_price" CASCADE;
DROP TABLE IF EXISTS public."cas_bunker_bunkering_por" CASCADE;
DROP TABLE IF EXISTS public."cas_bunker_consumption_sea" CASCADE;
DROP TABLE IF EXISTS public."cas_bunker_consumption_port" CASCADE;
DROP TABLE IF EXISTS public."cas_schedule_long_range" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_own_vessel_cost" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_port_charge" CASCADE;
DROP TABLE IF EXISTS public."cas_schedule_proforma" CASCADE;
DROP TABLE IF EXISTS public."cas_cost_ts_cost" CASCADE;
DROP TABLE IF EXISTS public."cas_vessel_capacity" CASCADE;
DROP TABLE IF EXISTS public."cas_vessel_info" CASCADE;
DROP TABLE IF EXISTS public."cas_week_period" CASCADE;
DROP TABLE IF EXISTS public."django_session" CASCADE;