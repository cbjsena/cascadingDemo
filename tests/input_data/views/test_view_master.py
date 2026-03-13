"""
Master 화면 테스트
Test Scenarios: MASTER_TRADE_001~005, MASTER_PORT_001~003, MASTER_LANE_001~003,
                MASTER_WEEK_PERIOD_001~003, MASTER_MENU_001~003
"""

from django.urls import reverse

import pytest

from input_data.models import BaseWeekPeriod, MasterLane, MasterPort, MasterTrade


@pytest.mark.django_db
class TestMasterTradeView:
    """Master Trade 목록/추가/삭제 테스트"""

    def test_trade_list(self, auth_client):
        """
        [MASTER_TRADE_001] Trade Info 목록 조회 및 데이터 표시 (DataTables API)
        """
        url = reverse("input_data:master_trade_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/master_trade_list.html" in [
            t.name for t in response.templates
        ]
        # DataTables API로 변경되었으므로 items 대신 menu_structure 확인
        assert "menu_structure" in response.context

    def test_trade_search(self, auth_client):
        """
        [MASTER_TRADE_002] 코드/이름으로 DataTables AJAX 검색 필터링
        """
        MasterTrade.objects.get_or_create(
            trade_code="FE1", defaults={"trade_name": "Far East 1"}
        )
        MasterTrade.objects.get_or_create(
            trade_code="EC2", defaults={"trade_name": "Europe Coast 2"}
        )

        # DataTables AJAX 요청 (draw 파라미터 포함)
        url = reverse("input_data:master_trade_list")
        response = auth_client.get(
            url, {"draw": "1", "start": "0", "length": "50", "search[value]": "FE"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # FE1 이 결과에 포함되어야 함
        trade_codes = [item["trade_code"] for item in data["data"]]
        assert "FE1" in trade_codes

    def test_trade_add_row_save(self, auth_client):
        """
        [MASTER_TRADE_003] 새 Trade 추가 후 DB 저장
        """
        url = reverse("input_data:master_trade_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "new_trade_code_0": "NEW_TRADE",
                "new_trade_name_0": "New Trade",
                "new_from_continent_0": "AS",
                "new_to_continent_0": "EU",
            },
        )

        assert response.status_code == 302
        assert MasterTrade.objects.filter(trade_code="NEW_TRADE").exists()
        obj = MasterTrade.objects.get(trade_code="NEW_TRADE")
        assert obj.trade_name == "New Trade"
        assert obj.from_continent_code == "AS"

    def test_trade_delete(self, auth_client):
        """
        [MASTER_TRADE_004] 선택 Trade 삭제 (참조 없는 경우)
        """
        MasterTrade.objects.get_or_create(
            trade_code="DEL_TRADE", defaults={"trade_name": "To Delete"}
        )

        url = reverse("input_data:master_trade_list")
        response = auth_client.post(
            url,
            {
                "action": "delete",
                "selected_pks": ["DEL_TRADE"],
            },
        )

        assert response.status_code == 302
        assert not MasterTrade.objects.filter(trade_code="DEL_TRADE").exists()

    def test_trade_delete_protect_error(self, auth_client):
        """
        [MASTER_TRADE_005] PROTECT FK 참조 시 삭제 에러 (base_/sce_ 가 참조하면 삭제 불가)
        이 테스트는 실제 참조 데이터가 있어야 ProtectedError 발생.
        base_vessel_capacity 등이 Trade FK를 참조하는 경우를 확인.
        """
        from input_data.models import BaseVesselCapacity

        trade, _ = MasterTrade.objects.get_or_create(
            trade_code="PROT_TRADE", defaults={"trade_name": "Protected Trade"}
        )
        lane, _ = MasterLane.objects.get_or_create(
            lane_code="PROT_LANE", defaults={"lane_name": "Protected Lane"}
        )

        # base_vessel_capacity가 이 trade를 참조
        BaseVesselCapacity.objects.create(
            trade=trade,
            lane=lane,
            vessel_code="VTST",
            voyage_number="0001",
            direction="E",
            vessel_capacity=5000,
            reefer_capacity=100,
        )

        url = reverse("input_data:master_trade_list")
        # ProtectedError -> Django 500 또는 view에서 catch 하지 않으면 에러
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            auth_client.post(
                url,
                {
                    "action": "delete",
                    "selected_pks": ["PROT_TRADE"],
                },
            )


@pytest.mark.django_db
class TestMasterPortView:
    """Master Port 목록/검색/추가 테스트"""

    def test_port_list(self, auth_client):
        """
        [MASTER_PORT_001] Port Info 목록 조회 (DataTables API)
        """
        url = reverse("input_data:master_port_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        # DataTables API로 변경되었으므로 items 대신 continent_codes 확인
        assert "continent_codes" in response.context

    def test_port_continent_filter(self, auth_client):
        """
        [MASTER_PORT_002] DataTables AJAX로 Continent 필터링
        """
        MasterPort.objects.update_or_create(
            port_code="PUS_AS",
            defaults={"port_name": "Pusan", "continent_code": "AS"},
        )
        MasterPort.objects.update_or_create(
            port_code="HAM_EU",
            defaults={"port_name": "Hamburg", "continent_code": "EU"},
        )

        # DataTables AJAX 요청
        url = reverse("input_data:master_port_list")
        response = auth_client.get(
            url, {"draw": "1", "start": "0", "length": "50", "continent": "AS"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # AS 대륙의 포트만 포함되어야 함
        port_codes = [item["port_code"] for item in data["data"]]
        assert "PUS_AS" in port_codes
        assert "HAM_EU" not in port_codes

    def test_port_add_row_save(self, auth_client):
        """
        [MASTER_PORT_003] 새 Port 추가 후 DB 저장
        """
        url = reverse("input_data:master_port_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "new_port_code_0": "TST_PORT",
                "new_port_name_0": "Test Port",
                "new_continent_code_0": "AS",
                "new_country_code_0": "KR",
            },
        )

        assert response.status_code == 302
        assert MasterPort.objects.filter(port_code="TST_PORT").exists()


@pytest.mark.django_db
class TestMasterLaneView:
    """Master Lane 목록/검색/추가 테스트"""

    def test_lane_list(self, auth_client):
        """
        [MASTER_LANE_001] Lane Info 목록 조회 (DataTables API)
        """
        url = reverse("input_data:master_lane_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        # DataTables API로 변경되었으므로 items 대신 menu_structure 확인
        assert "menu_structure" in response.context

    def test_lane_search(self, auth_client):
        """
        [MASTER_LANE_002] DataTables AJAX 코드/이름으로 검색 필터링
        """
        url = reverse("input_data:master_lane_list")
        # DataTables AJAX 요청
        response = auth_client.get(
            url, {"draw": "1", "start": "0", "length": "50", "search[value]": "FP"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # master_data fixture에 FP1이 존재
        lane_codes = [item["lane_code"] for item in data["data"]]
        assert "FP1" in lane_codes

    def test_lane_add_row_save(self, auth_client):
        """
        [MASTER_LANE_003] 새 Lane 추가 후 DB 저장
        """
        url = reverse("input_data:master_lane_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "new_lane_code_0": "NW1_TEST",
                "new_lane_name_0": "New Lane Test",
                "new_service_type_0": "FMC",
                "new_eff_from_0": "",
                "new_eff_to_0": "",
                "new_feeder_div_0": "",
            },
        )

        assert response.status_code == 302
        assert MasterLane.objects.filter(lane_code="NW1_TEST").exists()


@pytest.mark.django_db
class TestMasterWeekPeriodView:
    """Master Week Period 목록/검색/추가/삭제 테스트"""

    def test_week_period_list(self, auth_client):
        """
        [MASTER_WEEK_PERIOD_001] Week Period 목록 조회 (DataTables API)
        """
        url = reverse("input_data:master_week_period_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/master_week_period_list.html" in [
            t.name for t in response.templates
        ]
        # DataTables API로 변경되었으므로 menu_structure 확인
        assert "menu_structure" in response.context

    def test_week_period_search(self, auth_client):
        """
        [MASTER_WEEK_PERIOD_002] DataTables AJAX 연도/주차로 검색 필터링
        """
        from datetime import date

        BaseWeekPeriod.objects.get_or_create(
            base_year="2026",
            base_week="01",
            defaults={
                "base_month": "01",
                "week_start_date": date(2026, 1, 5),
                "week_end_date": date(2026, 1, 11),
            },
        )
        BaseWeekPeriod.objects.get_or_create(
            base_year="2026",
            base_week="02",
            defaults={
                "base_month": "01",
                "week_start_date": date(2026, 1, 12),
                "week_end_date": date(2026, 1, 18),
            },
        )

        # DataTables AJAX 요청
        url = reverse("input_data:master_week_period_list")
        response = auth_client.get(
            url, {"draw": "1", "start": "0", "length": "50", "search[value]": "01"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # 2026년 1주차 데이터가 포함되어야 함
        week_data = [item for item in data["data"] if item["base_week"] == "01"]
        assert len(week_data) > 0
        assert week_data[0]["base_year"] == "2026"

    def test_week_period_add_row_save(self, auth_client):
        """
        [MASTER_WEEK_PERIOD_003] 새 Week Period 추가 후 DB 저장
        """
        url = reverse("input_data:master_week_period_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "new_base_year_0": "2027",
                "new_base_week_0": "05",
                "new_base_month_0": "02",
                "new_week_start_date_0": "2027-01-31",
                "new_week_end_date_0": "2027-02-06",
            },
        )

        assert response.status_code == 302
        assert BaseWeekPeriod.objects.filter(base_year="2027", base_week="05").exists()
        obj = BaseWeekPeriod.objects.get(base_year="2027", base_week="05")
        assert obj.base_month == "02"


@pytest.mark.django_db
class TestMasterMenu:
    """Master 메뉴 구조 테스트"""

    def test_master_menu_position(self, auth_client):
        """
        [MASTER_MENU_001] Master 메뉴가 사이드바에 렌더링되는지 확인
        """
        url = reverse("input_data:master_trade_list")
        response = auth_client.get(url)

        content = response.content.decode("utf-8")
        # 사이드바에 Master 그룹의 메뉴가 있어야 함
        assert "Trade Info" in content
        assert "Port Info" in content
        assert "Lane Info" in content
        assert "Week Period" in content

    def test_master_context_keys(self, auth_client):
        """
        [MASTER_MENU_002] context에 menu_structure 존재 확인
        """
        url = reverse("input_data:master_trade_list")
        response = auth_client.get(url)

        ctx = response.context
        assert "menu_structure" in ctx
        assert "creation_menu_structure" in ctx

    def test_week_period_menu_link(self, auth_client):
        """
        [MASTER_MENU_003] Week Period 메뉴 링크 존재 확인
        """
        url = reverse("input_data:master_week_period_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        # Week Period 메뉴가 렌더링되어야 함
        assert "Week Period" in content
