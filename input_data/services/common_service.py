# input_data/services/common_service.py

from input_data.models import BaseDistance


def get_distance_between_ports(origin, destination):
    """
    [Common Logic] 포트 간 거리 조회 (Base 테이블 — 시나리오 독립)
    Return: (distance, eca_distance) 튜플
    """
    if not (origin and destination):
        return 0, 0

    dist_obj = BaseDistance.objects.filter(
        from_port_id=origin, to_port_id=destination
    ).first()

    if dist_obj:
        return dist_obj.distance, dist_obj.eca_distance

    return 0, 0
