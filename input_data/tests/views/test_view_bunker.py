"""
Bunker 화면 테스트
Test Scenarios: BUNKER_SEA_001~006, BUNKER_PORT_001~004, BUNKER_PRICE_001~005
"""

from django.urls import reverse

import pytest

from input_data.models import (
    BaseWeekPeriod,
    BunkerConsumptionPort,
    BunkerConsumptionSea,
    BunkerPrice,
    MasterLane,
    MasterTrade,
    ScenarioInfo,
)


@pytest.fixture
def bunker_scenario(db, user):
    """Bunker 테스트용 시나리오 2개 + BaseWeekPeriod (Bunker Price base_year_month select 전용)"""
    # BaseWeekPeriod: Bunker Price 모달의 base_year_month select에서만 사용
    # (Sea/Port에서는 base_year_month 필드가 제거되어 불필요)
    BaseWeekPeriod.objects.get_or_create(
        base_year="2026",
        base_week="01",
        defaults={
            "base_month": "01",
            "week_start_date": "2026-01-01",
            "week_end_date": "2026-01-07",
        },
    )
    BaseWeekPeriod.objects.get_or_create(
        base_year="2026",
        base_week="05",
        defaults={
            "base_month": "02",
            "week_start_date": "2026-01-29",
            "week_end_date": "2026-02-04",
        },
    )
    s1 = ScenarioInfo.objects.create(
        code="SC_BNK_01",
        description="Bunker Test 1",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    s2 = ScenarioInfo.objects.create(
        code="SC_BNK_02",
        description="Bunker Test 2",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    return s1, s2


@pytest.mark.django_db
class TestBunkerConsumptionSeaView:
    """Bunker Consumption Sea 화면 테스트"""

    @pytest.fixture
    def sea_data(self, db, bunker_scenario, user):
        s1, s2 = bunker_scenario
        BunkerConsumptionSea.objects.create(
            scenario=s1,
            vessel_capacity=1851,
            sea_speed=14.0,
            bunker_consumption=55.123,
            created_by=user,
            updated_by=user,
        )
        BunkerConsumptionSea.objects.create(
            scenario=s1,
            vessel_capacity=1851,
            sea_speed=16.0,
            bunker_consumption=70.456,
            created_by=user,
            updated_by=user,
        )
        BunkerConsumptionSea.objects.create(
            scenario=s2,
            vessel_capacity=4000,
            sea_speed=18.0,
            bunker_consumption=120.789,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2}

    def test_bunker_sea_list(self, auth_client, sea_data):
        """[BUNKER_SEA_001] 목록 조회 — 전체 데이터 표시"""
        s1 = sea_data["s1"]
        url = reverse("input_data:bunker_consumption_sea_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert b"Bunker Consumption Sea" in response.content
        assert len(response.context["items"]) == 2

    def test_bunker_sea_scenario_filter(self, auth_client, sea_data):
        """[BUNKER_SEA_002] 시나리오 필터 적용"""
        s1 = sea_data["s1"]
        url = reverse("input_data:bunker_consumption_sea_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert len(response.context["items"]) == 2

    def test_bunker_sea_search(self, auth_client, sea_data):
        """[BUNKER_SEA_003] 검색 (vessel_capacity or sea_speed)"""
        s1 = sea_data["s1"]
        url = reverse("input_data:bunker_consumption_sea_list")
        response = auth_client.get(url, {"scenario_id": s1.id, "search": "1851"})
        assert response.status_code == 200
        assert len(response.context["items"]) == 2

    def test_bunker_sea_add_row_save(self, auth_client, sea_data):
        """[BUNKER_SEA_004] Add Row 저장"""
        s1 = sea_data["s1"]
        url = reverse("input_data:bunker_consumption_sea_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_capacity_0": "2500",
                "new_sea_speed_0": "15.0",
                "new_bunker_consumption_0": "60.555",
            },
        )
        assert response.status_code == 302
        assert BunkerConsumptionSea.objects.filter(
            scenario=s1,
            vessel_capacity=2500,
            sea_speed="15.000",
        ).exists()

    def test_bunker_sea_delete(self, auth_client, sea_data):
        """[BUNKER_SEA_005] 행 삭제"""
        s1 = sea_data["s1"]
        pks = list(
            BunkerConsumptionSea.objects.filter(scenario=s1).values_list(
                "pk", flat=True
            )
        )
        url = reverse("input_data:bunker_consumption_sea_list")
        response = auth_client.post(
            url,
            {"action": "delete", "scenario_id": s1.id, "selected_pks": pks},
        )
        assert response.status_code == 302
        assert BunkerConsumptionSea.objects.filter(scenario=s1).count() == 0

    def test_bunker_sea_duplicate_skip(self, auth_client, sea_data):
        """[BUNKER_SEA_006] 중복 데이터 저장 시 skip"""
        from django.contrib.messages import get_messages

        s1 = sea_data["s1"]
        url = reverse("input_data:bunker_consumption_sea_list")
        # 이미 존재하는 (1851, 14.0) 데이터를 다시 저장
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_capacity_0": "1851",
                "new_sea_speed_0": "14.0",
                "new_bunker_consumption_0": "99.999",
            },
            follow=True,
        )
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        assert any("skipped" in m for m in msgs)
        # 기존 값 유지 확인
        obj = BunkerConsumptionSea.objects.get(
            scenario=s1,
            vessel_capacity=1851,
            sea_speed="14.000",
        )
        assert float(obj.bunker_consumption) == pytest.approx(55.123, abs=0.001)


@pytest.mark.django_db
class TestBunkerConsumptionPortView:
    """Bunker Consumption Port 화면 테스트"""

    @pytest.fixture
    def port_data(self, db, bunker_scenario, user):
        s1, s2 = bunker_scenario
        BunkerConsumptionPort.objects.create(
            scenario=s1,
            vessel_capacity=1851,
            port_stay_bunker_consumption=2.500,
            idling_bunker_consumption=1.200,
            pilot_inout_bunker_consumption=4.800,
            created_by=user,
            updated_by=user,
        )
        BunkerConsumptionPort.objects.create(
            scenario=s1,
            vessel_capacity=4000,
            port_stay_bunker_consumption=4.100,
            idling_bunker_consumption=2.300,
            pilot_inout_bunker_consumption=7.200,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2}

    def test_bunker_port_list(self, auth_client, port_data):
        """[BUNKER_PORT_001] 목록 조회 — 전체 데이터 표시"""
        s1 = port_data["s1"]
        url = reverse("input_data:bunker_consumption_port_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert b"Bunker Consumption Port" in response.content
        assert len(response.context["items"]) == 2

    def test_bunker_port_scenario_filter(self, auth_client, port_data):
        """[BUNKER_PORT_002] 시나리오 필터 적용"""
        s1 = port_data["s1"]
        url = reverse("input_data:bunker_consumption_port_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert len(response.context["items"]) == 2

    def test_bunker_port_add_row_save(self, auth_client, port_data):
        """[BUNKER_PORT_003] Add Row 저장"""
        s1 = port_data["s1"]
        url = reverse("input_data:bunker_consumption_port_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_capacity_0": "2500",
                "new_port_stay_bunker_consumption_0": "3.100",
                "new_idling_bunker_consumption_0": "1.800",
                "new_pilot_inout_bunker_consumption_0": "5.500",
            },
        )
        assert response.status_code == 302
        assert BunkerConsumptionPort.objects.filter(
            scenario=s1,
            vessel_capacity=2500,
        ).exists()

    def test_bunker_port_delete(self, auth_client, port_data):
        """[BUNKER_PORT_004] 행 삭제"""
        s1 = port_data["s1"]
        pks = list(
            BunkerConsumptionPort.objects.filter(scenario=s1).values_list(
                "pk", flat=True
            )
        )
        url = reverse("input_data:bunker_consumption_port_list")
        response = auth_client.post(
            url,
            {"action": "delete", "scenario_id": s1.id, "selected_pks": pks},
        )
        assert response.status_code == 302
        assert BunkerConsumptionPort.objects.filter(scenario=s1).count() == 0


@pytest.mark.django_db
class TestBunkerPriceView:
    """Bunker Price 화면 테스트"""

    @pytest.fixture
    def price_data(self, db, bunker_scenario, user):
        s1, s2 = bunker_scenario
        # Master 데이터 생성
        trade = MasterTrade.objects.create(trade_code="AEU")
        lane = MasterLane.objects.create(lane_code="AE1")

        BunkerPrice.objects.create(
            scenario=s1,
            base_year_month="202601",
            trade=trade,
            lane=lane,
            bunker_type="LSFO",
            bunker_price=650.500,
            created_by=user,
            updated_by=user,
        )
        BunkerPrice.objects.create(
            scenario=s1,
            base_year_month="202601",
            trade=trade,
            lane=lane,
            bunker_type="MGO",
            bunker_price=750.200,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "trade": trade, "lane": lane}

    def test_bunker_price_list(self, auth_client, price_data):
        """[BUNKER_PRICE_001] 목록 조회 — 전체 데이터 표시"""
        s1 = price_data["s1"]
        url = reverse("input_data:bunker_price_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert b"Bunker Price" in response.content
        assert len(response.context["items"]) == 2

    def test_bunker_price_scenario_filter(self, auth_client, price_data):
        """[BUNKER_PRICE_002] 시나리오 필터 적용"""
        s1 = price_data["s1"]
        url = reverse("input_data:bunker_price_list")
        response = auth_client.get(url, {"scenario_id": s1.id})
        assert response.status_code == 200
        assert len(response.context["items"]) == 2

    def test_bunker_price_search(self, auth_client, price_data):
        """[BUNKER_PRICE_003] 검색 (trade_code, lane_code, bunker_type)"""
        s1 = price_data["s1"]
        url = reverse("input_data:bunker_price_list")
        response = auth_client.get(url, {"scenario_id": s1.id, "search": "LSFO"})
        assert response.status_code == 200
        assert len(response.context["items"]) == 1

    def test_bunker_price_add_row_save(self, auth_client, price_data):
        """[BUNKER_PRICE_004] Add Row 저장"""
        s1 = price_data["s1"]
        trade = price_data["trade"]
        lane = price_data["lane"]
        url = reverse("input_data:bunker_price_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_base_year_month_0": "202602",
                "new_trade_0": trade.trade_code,
                "new_lane_0": lane.lane_code,
                "new_bunker_type_0": "LSFO",
                "new_bunker_price_0": "680.300",
            },
        )
        assert response.status_code == 302
        assert BunkerPrice.objects.filter(
            scenario=s1,
            base_year_month="202602",
            trade=trade,
            lane=lane,
            bunker_type="LSFO",
        ).exists()

    def test_bunker_price_delete(self, auth_client, price_data):
        """[BUNKER_PRICE_005] 행 삭제"""
        s1 = price_data["s1"]
        pks = list(BunkerPrice.objects.filter(scenario=s1).values_list("pk", flat=True))
        url = reverse("input_data:bunker_price_list")
        response = auth_client.post(
            url,
            {"action": "delete", "scenario_id": s1.id, "selected_pks": pks},
        )
        assert response.status_code == 302
        assert BunkerPrice.objects.filter(scenario=s1).count() == 0
