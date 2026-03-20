"""
시나리오 Export 서비스 테스트
- ScenarioExportService: 모델 탐색, JSON 직렬화, ZIP 생성
- Export View: 요청/상태/다운로드 엔드포인트
"""

import json
import os
import shutil
import tempfile
import zipfile

from django.urls import reverse

import pytest

from input_data.models import BunkerConsumptionPort, CanalFee, ScenarioInfo
from input_data.services.scenario_export_service import ScenarioExportService


@pytest.mark.django_db
class TestScenarioExportService:
    """ScenarioExportService 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self, db, user, master_data):
        self.user = user
        self.tmp_dir = tempfile.mkdtemp()
        self.scenario = ScenarioInfo.objects.create(
            description="Export Test Scenario",
            base_year_week="202601",
            scenario_type="WHAT_IF",
            status="ACTIVE",
            created_by=user,
            updated_by=user,
        )
        yield
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_export_creates_meta_json(self):
        """
        [IN_EXP_SVC_001] Export 실행 시 _meta.json이 생성되고 scenario_id 포함 검증
        """
        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        assert "_meta.json" in result["files"]
        assert result["meta"]["scenario_id"] == self.scenario.id
        assert result["meta"]["code"] == self.scenario.code

    def test_export_creates_zip(self):
        """
        [IN_EXP_SVC_002] Export 실행 시 ZIP 파일이 생성되는지 검증
        """
        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        assert "zip_path" in result
        assert os.path.exists(result["zip_path"])
        assert result["zip_path"].endswith(".zip")

    def test_export_zip_contains_meta(self):
        """
        [IN_EXP_SVC_003] ZIP 파일에 _meta.json이 포함되어 있는지 검증
        """
        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        with zipfile.ZipFile(result["zip_path"], "r") as zf:
            assert "_meta.json" in zf.namelist()

            meta = json.loads(zf.read("_meta.json"))
            assert meta["scenario_id"] == self.scenario.id

    def test_export_empty_scenario(self):
        """
        [IN_EXP_SVC_004] 빈 시나리오 Export 시 total_records == 0 검증
        """
        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        assert result["total_records"] == 0

    def test_export_with_canal_fee_data(self):
        """
        [IN_EXP_SVC_005] 데이터가 있는 시나리오에서 모델별 JSON 파일 생성 검증
        """
        CanalFee.objects.create(
            scenario=self.scenario,
            vessel_code="V001",
            direction="E",
            port_id="KRPUS",
            canal_fee=150000.00,
            created_by=self.user,
            updated_by=self.user,
        )

        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        assert result["total_records"] > 0
        # db_table 이름으로 파일 생성
        assert "sce_cost_canal_fee.json" in result["files"]

    def test_export_json_uses_django_encoder(self):
        """
        [IN_EXP_SVC_006] DjangoJSONEncoder로 Decimal/datetime이 직렬화되는지 검증
        """
        CanalFee.objects.create(
            scenario=self.scenario,
            vessel_code="V002",
            direction="W",
            port_id="JPTYO",
            canal_fee=999999.123456,
            created_by=self.user,
            updated_by=self.user,
        )

        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        with zipfile.ZipFile(result["zip_path"], "r") as zf:
            data = json.loads(zf.read("sce_cost_canal_fee.json"))

        assert len(data) == 1
        assert isinstance(data[0]["fee"], (int, float, str))

    def test_export_excludes_scenario_fk(self):
        """
        [IN_EXP_SVC_007] Export된 JSON에 scenario_id, id, audit 필드가 제외되고
        field_map에 따라 rename되는지 검증
        """
        CanalFee.objects.create(
            scenario=self.scenario,
            vessel_code="V003",
            direction="E",
            port_id="SGSIN",
            canal_fee=100000.00,
            created_by=self.user,
            updated_by=self.user,
        )

        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        with zipfile.ZipFile(result["zip_path"], "r") as zf:
            data = json.loads(zf.read("sce_cost_canal_fee.json"))

        record = data[0]
        # 제외된 필드
        assert "scenario_id" not in record
        assert "id" not in record
        assert "created_at" not in record
        assert "created_by_id" not in record
        assert "updated_at" not in record
        assert "updated_by_id" not in record
        # 원래 DB 필드명이 아닌 rename된 키
        assert "canal_fee" not in record  # → fee
        assert "port_id" not in record  # → port_code
        # rename 후 키가 존재
        assert "fee" in record
        assert "port_code" in record
        assert "vessel_code" in record
        assert "direction" in record

    def test_cleanup_removes_files(self):
        """
        [IN_EXP_SVC_008] cleanup()이 폴더와 ZIP을 모두 제거하는지 검증
        """
        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        service.export_all()

        assert os.path.exists(service.zip_path)

        service.cleanup()
        assert not os.path.exists(service.output_dir)
        assert not os.path.exists(service.zip_path)

    def test_progress_callback_called(self):
        """
        [IN_EXP_SVC_009] progress_callback이 호출되는지 검증
        """
        calls = []

        def callback(pct, step):
            calls.append((pct, step))

        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        service.export_all(progress_callback=callback)

        assert len(calls) > 0
        # 마지막 콜백이 100%인지
        assert calls[-1][0] == 100

    def test_export_nesting_bunker_consumption_port(self):
        """
        [IN_EXP_SVC_010] BunkerConsumptionPort Export 시 field_map + nesting 적용 검증
        Expected JSON:
          {
            "nominal_capacity": 2500,
            "consumption": {
              "consumption_for_berthing": "0.320",
              "consumption_for_idling": "0.000",
              "consumption_for_pilot": "1.200"
            }
          }
        """
        BunkerConsumptionPort.objects.create(
            scenario=self.scenario,
            vessel_capacity=2500,
            port_stay_bunker_consumption="0.320",
            idling_bunker_consumption="0.000",
            pilot_inout_bunker_consumption="1.200",
            created_by=self.user,
            updated_by=self.user,
        )

        service = ScenarioExportService(self.scenario.id, base_dir=self.tmp_dir)
        result = service.export_all()

        with zipfile.ZipFile(result["zip_path"], "r") as zf:
            data = json.loads(zf.read("sce_bunker_consumption_port.json"))

        record = data[0]
        # field_map: vessel_capacity → nominal_capacity
        assert record["nominal_capacity"] == 2500
        assert "vessel_capacity" not in record

        # nesting: consumption 그룹 존재
        assert "consumption" in record
        assert isinstance(record["consumption"], dict)

        consumption = record["consumption"]
        assert "consumption_for_berthing" in consumption
        assert "consumption_for_idling" in consumption
        assert "consumption_for_pilot" in consumption

        # nesting 멤버가 최상위에는 없어야 함
        assert "consumption_for_berthing" not in record
        assert "consumption_for_idling" not in record
        assert "consumption_for_pilot" not in record


@pytest.mark.django_db
class TestScenarioExportView:
    """Export View 통합 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self, db, auth_client, user, master_data):
        self.client = auth_client
        self.user = user
        self.scenario = ScenarioInfo.objects.create(
            description="View Export Test",
            base_year_week="202601",
            scenario_type="WHAT_IF",
            status="ACTIVE",
            created_by=user,
            updated_by=user,
        )

    def test_export_request_returns_task_id(self):
        """
        [IN_EXP_DIS_001] Export POST 요청 시 성공 응답 검증
        (EAGER 모드에서는 동기 실행 후 즉시 완료)
        """
        url = reverse(
            "input_data:scenario_export_request",
            kwargs={"scenario_id": self.scenario.id},
        )
        response = self.client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data
        assert data["scenario_id"] == self.scenario.id
        # EAGER 모드에서는 eager_result 포함
        assert "eager_result" in data
        assert data["eager_result"]["state"] == "SUCCESS"

    def test_export_and_download(self):
        """
        [IN_EXP_DIS_002] Export 요청 후 ZIP 다운로드까지 E2E 검증
        """
        # 1. Export 요청 (EAGER → 즉시 완료)
        url = reverse(
            "input_data:scenario_export_request",
            kwargs={"scenario_id": self.scenario.id},
        )
        resp = self.client.post(url)
        assert resp.status_code == 200

        # 2. 다운로드
        dl_url = reverse(
            "input_data:scenario_export_download",
            kwargs={"scenario_id": self.scenario.id},
        )
        dl_resp = self.client.get(dl_url)

        assert dl_resp.status_code == 200
        assert dl_resp["Content-Type"] == "application/zip"
        assert "attachment" in dl_resp["Content-Disposition"]

    def test_export_status_eager_mode(self):
        """
        [IN_EXP_DIS_003] EAGER 모드에서 상태 조회 시 항상 SUCCESS 반환
        """
        status_url = reverse(
            "input_data:scenario_export_status",
            kwargs={"task_id": "any-task-id"},
        )
        status_resp = self.client.get(status_url)

        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["state"] == "SUCCESS"
        assert data["progress"] == 100

    def test_export_download_404_when_no_file(self):
        """
        [IN_EXP_DIS_004] Export 미실행 상태에서 다운로드 시 404 반환 검증
        """
        dl_url = reverse(
            "input_data:scenario_export_download",
            kwargs={"scenario_id": self.scenario.id},
        )
        dl_resp = self.client.get(dl_url)

        assert dl_resp.status_code == 404
