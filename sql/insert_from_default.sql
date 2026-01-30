
INSERT INTO cas_cost_distance (
    created_at,
    updated_at,
    from_port_code,
    to_port_code,
    distance,
    eca_distance,
    created_by_id,
	updated_by_id,
    data_id 
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
    'default_id' as data_id
FROM default_cost_distance d  
cROSS JOIN auth_user a
where a.username = 'cascading' ;
commit;
SELECT id, a.username
FROM auth_user;

select data_id, count(*) 
 from cas_cost_distance
group by data_id 