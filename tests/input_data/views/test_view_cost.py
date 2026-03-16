"""
Cost 화면 테스트
Test Scenarios: IN_CF_DIS_001~005, IN_DST_DIS_001~005, IN_TSC_DIS_001~007,
                IN_CSV_DIS_001~003, IN_CSV_DIS_004~003
"""

import io

from django.urls import reverse

import pytest

from common import messages
from input_data.models import (
    BaseVesselInfo,
    CanalFee,
    Distance,
    ScenarioInfo,
    TSCost,
)


@pytest.fixture
def cost_scenario(db, user):
    """Cost 테스트용 시나리오 2개"""
    s1 = ScenarioInfo.objects.create(
        code="SC_COST_01",
        description="Cost Test 1",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    s2 = ScenarioInfo.objects.create(
        code="SC_COST_02",
        description="Cost Test 2",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    return s1, s2


@pytest.fixture
def base_vessel_for_cost(db):
    """Canal Fee에서 Vessel 선택용 Base 데이터"""
    BaseVesselInfo.objects.create(vessel_code="V001", vessel_name="Ship 1", own_yn="O")


@pytest.mark.django_db
class TestCanalFeeView:
    """Canal Fee 목록/필터/검색/추가/삭제 테스트"""

    @pytest.fixture
    def canal_fee_data(self, db, cost_scenario, user, master_data):
        """테스트를 위한 기초 데이터 세팅"""
        s1, s2 = cost_scenario
        cf1 = CanalFee.objects.create(
            scenario=s1,
            vessel_code="V001",
            direction="E",
            port_id="KRPUS",
            canal_fee=150000.00,
            created_by=user,
            updated_by=user,
        )
        cf2 = CanalFee.objects.create(
            scenario=s2,
            vessel_code="V002",
            direction="W",
            port_id="JPTYO",
            canal_fee=200000.00,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "cf1": cf1, "cf2": cf2}

    def test_canal_fee_list(self, auth_client, canal_fee_data):
        """
        [IN_CF_DIS_001] Canal Fee 목록 조회
        Canal Fee 페이지 정상 로드 및 context 검증
        """
        url = reverse("input_data:canal_fee_list")
        response = auth_client.get(url)

        # 1. Status 200 OK
        assert response.status_code == 200

        # 2. Context 검증 (변경된 extra_context 반영)
        assert "scenarios" in response.context
        assert "filter_ports" in response.context  # cost.py의 extra_context
        assert "filter_vessels" in response.context
        assert "search_params" in response.context

    def test_canal_fee_scenario_filter(self, auth_client, canal_fee_data):
        """
        [IN_CF_DIS_002] Canal Fee 시나리오 필터
        시나리오 선택 시 해당 데이터만 표시 검증
        """
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")

        # s1 시나리오 선택
        response = auth_client.get(url, {"scenario_id": s1.id})

        items = response.context["items"]
        vessel_codes = [item.vessel_code for item in items]

        # 1. scenario_id=1의 데이터(V001)만 표시
        assert "V001" in vessel_codes
        # 2. 다른 시나리오 데이터(V002) 미표시
        assert "V002" not in vessel_codes

    def test_canal_fee_search(self, auth_client, canal_fee_data):
        """
        [IN_CF_DIS_003] Canal Fee 검색 필터링
        Vessel/Port 코드 검색 검증
        """
        # s1 시나리오 내에서 검색 진행 (V001, KRPUS 존재)
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")

        response = auth_client.get(url, {"scenario_id": s1.id, "search": "KRPUS"})

        items = response.context["items"]

        # 1. port_code에 'KRPUS' 포함하는 데이터 표시
        assert len(items) >= 1
        assert any(item.port_id == "KRPUS" for item in items)

    def test_canal_fee_add_row_save(self, auth_client, canal_fee_data):
        """
        [IN_CF_DIS_004] Canal Fee 모달 추가 저장
        모달에서 새 Canal Fee 입력 후 DB 저장 검증
        """
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")

        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_code_0": "V001",
                "new_direction_0": "W",
                "new_port_code_0": "JPTYO",
                "new_canal_fee_0": "180000.50",
            },
        )

        # 1. Redirect 302 (scenario_id 유지)
        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url

        # 2. CanalFee에 해당 레코드 생성됨
        assert CanalFee.objects.filter(
            scenario=s1, vessel_code="V001", direction="W", port_id="JPTYO"
        ).exists()

        # 값 정확성 검증
        obj = CanalFee.objects.get(
            scenario=s1, vessel_code="V001", direction="W", port_id="JPTYO"
        )
        assert float(obj.canal_fee) == 180000.50

    def test_canal_fee_delete(self, auth_client, canal_fee_data):
        """
        [IN_CF_DIS_005] Canal Fee 삭제
        선택 Canal Fee 삭제 검증
        """
        cf1 = canal_fee_data["cf1"]
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")

        response = auth_client.post(
            url,
            {
                "action": "delete",
                "scenario_id": s1.id,
                "selected_pks": [cf1.pk],
            },
        )

        # 1. Redirect 302 (scenario_id 유지)
        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url

        # 2. pk=N DB에서 삭제됨
        assert not CanalFee.objects.filter(pk=cf1.pk).exists()


@pytest.mark.django_db
class TestDistanceView:
    """Distance 목록/필터/검색/추가/삭제 테스트"""

    @pytest.fixture
    def distance_data(self, db, cost_scenario, user, master_data):
        """마스터 데이터(master_data)를 주입하여 Port 참조 무결성 확보"""
        s1, s2 = cost_scenario
        d1 = Distance.objects.create(
            scenario=s1,
            from_port_id="KRPUS",
            to_port_id="JPTYO",
            distance=500,
            eca_distance=100,
            created_by=user,
            updated_by=user,
        )
        d2 = Distance.objects.create(
            scenario=s2,
            from_port_id="JPTYO",
            to_port_id="USLAX",
            distance=5000,
            eca_distance=200,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "d1": d1, "d2": d2}

    def test_distance_list(self, auth_client, distance_data):
        """
        [IN_DST_DIS_001] Distance 목록 조회 및 Context 검증
        """
        url = reverse("input_data:distance_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "scenarios" in response.context
        assert "filter_ports" in response.context  # 동적 필터용
        assert "ports" in response.context  # 모달 입력용 전체 포트
        assert "search_params" in response.context

    def test_distance_scenario_filter(self, auth_client, distance_data):
        """
        [IN_DST_DIS_002] 시나리오 선택 시 해당 데이터만 표시
        """
        s1 = distance_data["s1"]
        url = reverse("input_data:distance_list")
        response = auth_client.get(url, {"scenario_id": s1.id})

        items = response.context["items"]
        from_ports = [item.from_port_id for item in items]
        assert "KRPUS" in from_ports
        assert "JPTYO" not in from_ports  # s2 데이터는 안 보여야 함

    def test_distance_search(self, auth_client, distance_data):
        """
        [IN_DST_DIS_003] Port 코드 검색 필터링
        """
        s1 = distance_data["s1"]
        url = reverse("input_data:distance_list")
        # s1 시나리오 내에서 검색 수행
        response = auth_client.get(url, {"scenario_id": s1.id, "search": "KRPUS"})

        items = response.context["items"]
        assert len(items) >= 1
        assert any(
            item.from_port_id == "KRPUS" or item.to_port_id == "KRPUS" for item in items
        )

    def test_distance_add_row_save(self, auth_client, distance_data):
        """
        [IN_DST_DIS_004] 모달에서 Distance 추가 후 DB 저장
        """
        s1 = distance_data["s1"]
        url = reverse("input_data:distance_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_from_port_0": "USLAX",
                "new_to_port_0": "KRPUS",
                "new_distance_0": "6000",
                "new_eca_distance_0": "300",
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        obj = Distance.objects.get(
            scenario=s1, from_port_id="USLAX", to_port_id="KRPUS"
        )
        assert obj.distance == 6000
        assert obj.eca_distance == 300

    def test_distance_delete(self, auth_client, distance_data):
        """
        [IN_DST_DIS_005] 선택 Distance 삭제
        """
        d1 = distance_data["d1"]
        s1 = distance_data["s1"]
        url = reverse("input_data:distance_list")
        response = auth_client.post(
            url,
            {
                "action": "delete",
                "scenario_id": s1.id,
                "selected_pks": [d1.pk],
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        assert not Distance.objects.filter(pk=d1.pk).exists()


@pytest.mark.django_db
class TestTSCostView:
    """TS Cost 목록/필터/검색/추가/삭제/중복 테스트"""

    @pytest.fixture
    def ts_cost_data(self, db, cost_scenario, user, master_data):
        """마스터 데이터(master_data) 주입"""
        s1, s2 = cost_scenario
        tc1 = TSCost.objects.create(
            scenario=s1,
            base_year_month="202601",
            lane_id="TEST_LANE",
            port_id="KRPUS",
            ts_cost=5000,
            created_by=user,
            updated_by=user,
        )
        tc2 = TSCost.objects.create(
            scenario=s2,
            base_year_month="202602",
            lane_id="FE1",
            port_id="JPTYO",
            ts_cost=8000,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "tc1": tc1, "tc2": tc2}

    def test_ts_cost_list(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_001] TS Cost 목록 조회
        """
        url = reverse("input_data:ts_cost_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "scenarios" in response.context
        assert "filter_lanes" in response.context
        assert "filter_ports" in response.context
        assert "lanes" in response.context
        assert "ports" in response.context
        assert "base_year_month_choices" in response.context
        assert "search_params" in response.context

    def test_ts_cost_scenario_filter(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_002] 시나리오 선택 시 해당 데이터만 표시
        """
        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        response = auth_client.get(url, {"scenario_id": s1.id})

        items = response.context["items"]
        lane_codes = [item.lane_id for item in items]
        assert "TEST_LANE" in lane_codes
        assert "FE1" not in lane_codes

    def test_ts_cost_base_year_month_filter(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_007] Base Year Month 필터링
        """
        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        response = auth_client.get(
            url, {"scenario_id": s1.id, "base_year_month": "202601"}
        )

        items = response.context["items"]
        assert len(items) >= 1
        assert all(item.base_year_month == "202601" for item in items)
        assert all(item.base_year_month != "202602" for item in items)

    def test_ts_cost_search(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_003] Lane/Port 코드 검색 필터링
        """
        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        response = auth_client.get(url, {"scenario_id": s1.id, "search": "KRPUS"})

        items = response.context["items"]
        assert len(items) >= 1
        assert all(item.port_id == "KRPUS" for item in items)

    def test_ts_cost_add_row_save(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_004] 모달에서 TS Cost 추가 후 DB 저장
        """
        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_base_year_month_0": "202603",
                "new_lane_code_0": "FE1",
                "new_port_code_0": "JPTYO",
                "new_ts_cost_0": "12000",
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        obj = TSCost.objects.get(
            scenario=s1,
            base_year_month="202603",
            lane_id="FE1",
            port_id="JPTYO",
        )
        assert obj.ts_cost == 12000

    def test_ts_cost_delete(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_005] 선택 TS Cost 삭제
        """
        tc1 = ts_cost_data["tc1"]
        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        response = auth_client.post(
            url,
            {
                "action": "delete",
                "scenario_id": s1.id,
                "selected_pks": [tc1.pk],
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        assert not TSCost.objects.filter(pk=tc1.pk).exists()

    def test_ts_cost_duplicate_skip(self, auth_client, ts_cost_data):
        """
        [IN_TSC_DIS_006] 동일 scenario+base_year_month+lane+port 중복 저장 시 skip + 경고
        """
        from django.contrib.messages import get_messages

        s1 = ts_cost_data["s1"]
        url = reverse("input_data:ts_cost_list")
        # tc1과 동일한 키 조합: 202601, TEST_LANE, KRPUS
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_base_year_month_0": "202601",
                "new_lane_code_0": "TEST_LANE",
                "new_port_code_0": "KRPUS",
                "new_ts_cost_0": "9999",
            },
            follow=True,
        )

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        assert any("skipped" in m for m in msgs)

        # 기존 값 유지 확인 (Update가 아니라 Skip 되어야 함)
        obj = TSCost.objects.get(
            scenario=s1,
            base_year_month="202601",
            lane_id="TEST_LANE",
            port_id="KRPUS",
        )
        assert obj.ts_cost == 5000


@pytest.mark.django_db
class TestCsvDownloadUpload:
    """CSV Download / Upload 공통 기능 테스트 (Canal Fee 기준)"""

    @pytest.fixture
    def canal_fee_data(self, db, cost_scenario, user, master_data):
        s1, s2 = cost_scenario

        CanalFee.objects.create(
            scenario=s1,
            vessel_code="V001",
            direction="E",
            port_id="KRPUS",
            canal_fee=150000.00,
            created_by=user,
            updated_by=user,
        )
        CanalFee.objects.create(
            scenario=s1,
            vessel_code="V002",
            direction="W",
            port_id="JPTYO",
            canal_fee=200000.00,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2}

    def test_csv_download(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_001] CSV 다운로드 시 올바른 content-type과 데이터 검증
        """
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {"action": "csv_download", "scenario_id": s1.id},
        )

        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        assert "attachment" in response["Content-Disposition"]

        # CSV 내용 검증 (헤더는 DB 컬럼명)
        content = response.content.decode("utf-8-sig")
        lines = [line for line in content.strip().split("\n") if line.strip()]
        assert len(lines) >= 3  # 헤더 + 2 데이터 행
        assert "scenario_code" in lines[0]
        assert "vessel_code" in lines[0]
        assert "V001" in content
        assert "V002" in content

    def test_csv_download_scenario_filter(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_002] 시나리오 미선택 시에도 다운로드 가능 (전체)
        """
        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {"action": "csv_download", "scenario_id": ""},
        )
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]

    def test_csv_download_has_scenario_code_column(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_003] CSV에 scenario_code 컬럼이 포함되고 값이 정확한지 검증
        """
        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {"action": "csv_download", "scenario_id": s1.id},
        )

        content = response.content.decode("utf-8-sig")
        lines = [line for line in content.strip().split("\n") if line.strip()]
        assert len(lines) >= 2
        # 데이터 행의 첫 번째 컬럼이 시나리오 코드
        assert lines[1].startswith("SC_COST_01")

    def test_csv_upload(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_004] CSV 업로드 시 DB에 데이터 저장 검증
        """
        s1 = canal_fee_data["s1"]
        # 헤더는 DB 컬럼명 사용
        csv_content = (
            "scenario_code,vessel_code,direction,port_code,canal_fee\n"
            "SC_COST_01,V099,E,SGSIN,999999.50\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8-sig"))
        csv_file.name = "test_upload.csv"

        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {
                "action": "csv_upload",
                "scenario_id": s1.id,
                "csv_file": csv_file,
            },
        )

        assert response.status_code == 302
        obj = CanalFee.objects.get(
            scenario=s1, vessel_code="V099", direction="E", port_id="SGSIN"
        )
        assert obj.canal_fee == 999999.50

    def test_csv_upload_no_file(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_005] 파일 미선택 시 에러 메시지 검증
        """
        from django.contrib.messages import get_messages

        s1 = canal_fee_data["s1"]
        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {"action": "csv_upload", "scenario_id": s1.id},
            follow=True,
        )

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        assert any(messages.FILE_NOT_SELECTED in m for m in msgs)

    def test_csv_upload_no_scenario(self, auth_client, canal_fee_data):
        """
        [IN_CSV_DIS_006] 시나리오 미선택 시 에러 메시지 검증
        """
        from django.contrib.messages import get_messages

        csv_content = (
            "scenario_code,vessel_code,direction,port_code,canal_fee\n"
            "SC_COST_01,V099,E,SGSIN,999999.50\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8-sig"))
        csv_file.name = "test_upload.csv"

        url = reverse("input_data:canal_fee_list")
        response = auth_client.post(
            url,
            {
                "action": "csv_upload",
                "scenario_id": "",
                "csv_file": csv_file,
            },
            follow=True,
        )

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        assert any("scenario" in m.lower() for m in msgs)
        # 데이터가 생성되지 않았는지 확인
        assert not CanalFee.objects.filter(vessel_code="V099").exists()
