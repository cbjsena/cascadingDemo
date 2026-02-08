CREATE TABLE public.default_schedule_proforma (
	lane_code varchar(10) NOT NULL,
	proforma_name varchar(30) NOT NULL,
	lane_standard bool NULL,
	duration numeric(5, 1) NOT NULL,
	declared_capacity varchar(5) NOT NULL,
	declared_count int4 NOT NULL,
	direction varchar(2) NOT NULL,
	port_code varchar(10) NOT NULL,
	calling_port_indicator_seq varchar(2) NOT NULL,
	calling_port_seq int4 NOT NULL,
	turn_port_info_code varchar(3) NOT NULL,
	pilot_in_hours numeric(5, 3) NOT NULL,
	etb_day_code varchar(3) NOT NULL,
	etb_day_time varchar(4) NOT NULL,
	etb_day_number int4 NOT NULL,
	actual_work_hours numeric(5, 3) NOT NULL,
	etd_day_code varchar(3) NOT NULL,
	etd_day_time varchar(4) NOT NULL,
	etd_day_number int4 NOT NULL,
	pilot_out_hours numeric(5, 3) NOT NULL,
	link_distance int4 NOT NULL,
	link_eca_distance int4 NULL,
	link_speed numeric(5, 3) NULL,
	sea_hours numeric(5, 3) NULL,
	terminal_code varchar(10) NOT NULL,
	CONSTRAINT default_schedule_proforma_pkey PRIMARY KEY (lane_code, proforma_name, direction, calling_port_indicator_seq,port_code)
);


CREATE TABLE public.default_schedule_long_range (
	lane_code varchar(10) NOT NULL,
	vessel_code varchar(10) NOT NULL,
	voyage_number varchar(20) NOT NULL,
	direction varchar(2) NOT NULL,
	start_port_berthing_year_week varchar(6) NOT NULL,
	proforma_name varchar(30) NOT NULL,
	port_code varchar(10) NOT NULL,
	calling_port_indicator_seq varchar(2) NOT NULL,
	calling_port_seq int4 NOT NULL,
	schedule_change_status_code varchar(1) NULL,
	eta_initial_arrival timestamptz NULL,
	etb_initial_berthing timestamptz NULL,
	etd_initial_departure timestamptz NULL,
	terminal_code varchar(10) NULL,
	CONSTRAINT default_schedule_long_range_pkey PRIMARY KEY (lane_code, vessel_code,voyage_number, direction,calling_port_indicator_seq, port_code )
);


-- ##################### vessel	#####################
CREATE TABLE public.default_vessel_info (
	vessel_code varchar(4) NOT NULL,
	vessel_name varchar(50) NOT NULL,
	nominal_capacity int4 NOT NULL,
	own_yn varchar(1) NOT NULL,
	delivery_port_code varchar(10) NULL,
	delivery_date timestamptz NULL,
	redelivery_port_code varchar(10) NULL,
	redelivery_date timestamptz NULL,
	next_dock_port_code varchar(10) NULL,
	next_dock_in_date timestamptz NULL,
	next_dock_out_date timestamptz NULL,
	built_port_code varchar(10) NULL,
	built_date varchar(50) NULL,
	CONSTRAINT default_vessel_info_pkey PRIMARY KEY (vessel_code)
);


-- ##################### cost	#####################
CREATE TABLE public.default_cost_canal_fee (
	vessel_code varchar(10) NOT NULL,
	direction varchar(2) NOT NULL,
	port_code varchar(10) NOT NULL,
	canal_fee numeric(15, 6) NOT NULL,
	CONSTRAINT default_cost_canal_fee_pkey PRIMARY KEY (vessel_code, direction, port_code)
);

CREATE TABLE public.default_cost_distance (
	from_port_code varchar(10) NOT NULL,
	to_port_code varchar(10) NOT NULL,
	distance numeric(6) NOT NULL,
	eca_distance numeric(6) NOT NULL,
	CONSTRAINT default_cost_distance_pkey PRIMARY KEY (from_port_code, to_port_code)
);


CREATE TABLE public.default_cost_exchange_rate (
	base_year_month varchar(6) NOT NULL,
	currency_code varchar(3) NOT NULL,
	exchange_rate numeric(15, 6) NOT NULL,
	CONSTRAINT default_cost_exchange_rate_pkey PRIMARY KEY (base_year_month, currency_code)
);


CREATE TABLE public.default_cost_ts_cost (
	base_year_month varchar(6) NOT NULL,
	port_code varchar(10) NOT NULL,
	full_empty_code varchar(1) NOT NULL,
	container_code varchar(4) NOT NULL,
	currency_code varchar(3) NOT NULL,
	ts_cost int4 NOT NULL,
	CONSTRAINT default_cost_ts_cost_pkey PRIMARY KEY (base_year_month, port_code, full_empty_code, container_code, currency_code)
);

-- ##################### bunker	#####################
CREATE TABLE public.default_bunker_price (
	base_year_month varchar(6) NOT NULL,
	trade_code varchar(10) NOT NULL,
	lane_code varchar(10) NOT NULL,
	bunker_type varchar(4) NOT NULL,
	bunker_price numeric(10, 3) NOT null,
	CONSTRAINT default_bunker_bunker_price_pkey UNIQUE (base_year_month, trade_code, lane_code, bunker_type)
);

CREATE TABLE public.default_bunker_consumption_port (
	base_year_month varchar(6) NOT NULL,
	nominal_capacity int4 NOT NULL,
	port_stay_bunker_consumption numeric(5, 3) NOT NULL,
	idling_bunker_consumption numeric(5, 3) NOT NULL,
	pilot_inout_bunker_consumption numeric(5, 3) NOT NULL,
	CONSTRAINT default_bunker_consumption_port_uniq UNIQUE (base_year_month, nominal_capacity)
);

CREATE TABLE public.default_bunker_consumption_sea (
	base_year_month varchar(6) NOT NULL,
	nominal_capacity int4 NOT NULL,
	sea_speed numeric(5, 1) NOT NULL,
	bunker_consumption numeric(25, 13) NOT NULL,
	CONSTRAINT default_bunker_consumption_sea_pkey UNIQUE (base_year_month, nominal_capacity, sea_speed)
);

-- ##################### master	#####################
CREATE TABLE public.default_master_week_period (
	base_year int4 NOT NULL,
	base_week int4 NOT NULL,
	base_month int4 NOT NULL,
	week_start_date timestamptz NOT NULL,
	week_end_date timestamptz NOT NULL,
	CONSTRAINT default_master_week_period_pkey PRIMARY KEY (base_year, base_week)
);