from datetime import datetime

from input_data.models import (
    CascadingSchedule,
    CascadingScheduleDetail,
    ProformaSchedule,
    ScenarioInfo,
)


class CascadingService:
    """
    Cascading Schedule 화면 데이터 조회 및 DB 저장 전담 서비스
    """

    def get_cascading_data(self, scenario_id, lane_code, proforma_name):
        """저장된 Cascading 데이터 불러오기"""
        master_proforma = ProformaSchedule.objects.filter(
            scenario_id=scenario_id, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if not master_proforma:
            return None

        cascading = CascadingSchedule.objects.filter(
            scenario_id=scenario_id, proforma=master_proforma
        ).first()

        if not cascading:
            return None

        details = cascading.details.all().order_by("id")
        rows = [
            {
                "vessel_code": d.vessel_code,
                "vessel_start_date": (
                    d.initial_start_date.strftime("%Y-%m-%d")
                    if d.initial_start_date
                    else ""
                ),
            }
            for d in details
        ]

        return {
            "header": {
                "apply_start_date": (
                    cascading.start_date.strftime("%Y-%m-%d")
                    if cascading.start_date
                    else ""
                ),
                "apply_end_date": (
                    cascading.end_date.strftime("%Y-%m-%d")
                    if cascading.end_date
                    else ""
                ),
                "own_vessels": cascading.own_vessels,
            },
            "details": rows,
        }

    def save_cascading(self, post_data, user):
        """화면 입력을 받아 Cascading 테이블(Master & Detail)에 저장"""
        scenario_id = post_data.get("scenario_id")
        lane_code = post_data.get("lane_code")
        proforma_name = post_data.get("proforma_name")
        start_date_str = post_data.get("apply_start_date")
        end_date_str = post_data.get("apply_end_date")

        vessel_codes = post_data.getlist("vessel_code[]")
        vessel_start_dates = post_data.getlist("vessel_start_date[]")

        if not (
            scenario_id
            and lane_code
            and proforma_name
            and start_date_str
            and end_date_str
        ):
            raise ValueError("Missing required fields for Cascading.")

        scenario = ScenarioInfo.objects.get(id=scenario_id)
        master_proforma = ProformaSchedule.objects.filter(
            scenario=scenario, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if not master_proforma:
            raise ValueError("Proforma Schedule not found.")

        # 1. 기존 데이터 삭제 후 Master 재생성
        CascadingSchedule.objects.filter(
            scenario=scenario, proforma=master_proforma
        ).delete()

        cascading = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=master_proforma,
            cascading_seq=1,
            own_vessels=len(vessel_codes),
            start_date=datetime.strptime(start_date_str, "%Y-%m-%d").date(),
            end_date=datetime.strptime(end_date_str, "%Y-%m-%d").date(),
            created_by=user,
            updated_by=user,
        )

        # 2. Detail 데이터 생성
        details_to_create = []
        for v_code, v_date in zip(vessel_codes, vessel_start_dates):
            if v_code and v_date:
                details_to_create.append(
                    CascadingScheduleDetail(
                        cascading=cascading,
                        vessel_code=v_code,
                        initial_start_date=datetime.strptime(v_date, "%Y-%m-%d").date(),
                        created_by=user,
                        updated_by=user,
                    )
                )
        if details_to_create:
            CascadingScheduleDetail.objects.bulk_create(details_to_create)

        return cascading
