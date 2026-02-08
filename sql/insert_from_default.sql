
INSERT INTO cas_cost_distance (
    created_at,
    updated_at,
    from_port_code,
    to_port_code,
    distance,
    eca_distance,
    created_by_id,
	updated_by_id,
    scenario_id
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
    'default_id' as scenario_id
FROM default_cost_distance d  
cROSS JOIN auth_user a
where a.username = 'cascading' ;
commit;
SELECT id, a.username
FROM auth_user;

select scenario_id, count(*)
 from cas_cost_distance
group by scenario_id