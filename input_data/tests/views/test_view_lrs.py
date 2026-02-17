from datetime import timedelta

import pytest

from django.urls import reverse
from django.utils import timezone

from input_data.models import LongRangeSchedule


@pytest.mark.django_db
class TestLongRangeView:
    """
    LRS 생성 화면 및 POST 요청 테스트
    """

    def test_view_lrs_create_page(self, auth_client):
        """[LRS_VIEW_001] 생성 화면 진입"""
        url = reverse("input_data:long_range_create")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "input_data/long_range_create.html" in [
            t.name for t in response.templates
        ]

    def test_view_lrs_create_post(self, auth_client, sample_schedule):
        """[LRS_VIEW_002] POST 요청으로 생성 성공"""
        url = reverse("input_data:long_range_create")

        # Form Data
        data = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
            "apply_end_date": (timezone.now() + timedelta(days=20)).strftime(
                "%Y-%m-%d"
            ),
            "own_vessel_count": "1",
            "vessel_code[]": ["V_OWN"],
            "vessel_start_date[]": [timezone.now().strftime("%Y-%m-%d")],
        }

        response = auth_client.post(url, data, follow=True)

        # Assertions
        assert response.status_code == 200
        # 메시지 확인
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert any("successfully" in str(m) for m in messages)

        # DB 확인
        assert LongRangeSchedule.objects.filter(vessel_code="V_OWN").exists()
