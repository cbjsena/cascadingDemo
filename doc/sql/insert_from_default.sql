CREATE TABLE public.default_cost_distance (
	from_port_code varchar(10) NOT NULL,
	to_port_code varchar(10) NOT NULL,
	distance int4 NOT NULL,
	eca_distance int4 NOT NULL,
	CONSTRAINT default_cost_distance_pkey PRIMARY KEY (from_port_code, to_port_code)
);

INSERT INTO cas_cost_distance (
    created_at,
    updated_at,
    from_port_code,
    to_port_code,
    distance,
    eca_distance,
    created_by_id,
	updated_by_id,
    "DATA_ID"
)
SELECT
    now(),
    now(),
    from_port_code,
    to_port_code,
    distance,
    eca_distance,
    a.id,
    a.id,
    'default' as data_id
FROM default_cost_distance d  
cROSS JOIN auth_user a
where a.username = 'cascading' ;

SELECT id, a.username
FROM auth_user;

select * 
 from cas_cost_distance