CREATE TABLE public.default_schedule_proforma (
	lane_code varchar(10) NOT NULL,
	proforma_name varchar(30) NOT NULL,
	service_lane_standard bool NULL,
	duration numeric(5, 1) NOT NULL,
	standard_service_speed numeric(5, 3) NOT NULL,
	declared_capacity varchar(5) NOT NULL,
	declared_count int4 NOT NULL,
	direction varchar(2) NOT NULL,
	port_code varchar(10) NOT NULL,
	calling_port_indicator_seq varchar(2) NOT NULL,
	calling_port_seq int4 NOT NULL,
	turn_port_pair_code varchar(3) NOT NULL,
	turn_port_system_code varchar(3) NOT NULL,
	pilot_in_hours numeric(5, 3) NOT NULL,
	etb_day_code varchar(3) NOT NULL,
	etb_day_time varchar(4) NOT NULL,
	etb_day_number int4 NOT NULL,
	etd_day_code varchar(3) NOT NULL,
	etd_day_time varchar(4) NOT NULL,
	etd_day_number int4 NOT NULL,
	actual_work_hours numeric(5, 3) NOT NULL,
	pilot_out_hours numeric(5, 3) NOT NULL,
	link_distance int4 NOT NULL,
	link_speed numeric(5, 3) NOT NULL,
	sea_hours numeric(5, 3) NOT NULL,
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
	terminal_code varchar(10) null,
	CONSTRAINT default_schedule_long_range_pkey PRIMARY KEY (lane_code, vessel_code,voyage_number, direction,calling_port_indicator_seq, port_code )
);

CREATE TABLE public.default_cost_distance (
	from_port_code varchar(10) NOT NULL,
	to_port_code varchar(10) NOT NULL,
	distance int4 NOT NULL,
	eca_distance int4 NOT NULL,
	CONSTRAINT default_cost_distance_pkey PRIMARY KEY (from_port_code, to_port_code)
);