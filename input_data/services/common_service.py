# input_data/services/common_service.py (신규 또는 기존 서비스 파일)

from input_data.models import Distance


def get_distance_between_ports(scenario_id, origin, destination):
    """
    [Common Logic] 포트 간 거리 조회
    Return: (distance, eca_distance) 튜플
    """
    if not (origin and destination):
        return 0, 0

    dist_obj = Distance.objects.filter(
        scenario_id=scenario_id,
        from_port_code=origin,
        to_port_code=destination
    ).first()

    if dist_obj:
        return dist_obj.distance, dist_obj.eca_distance

    return 0, 0