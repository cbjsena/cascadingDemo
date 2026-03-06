from datetime import datetime, timedelta

from common import messages as msg
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
        """[Edit 모드용] Cascading 데이터를 불러옵니다."""
        # 1. Master Proforma와 Cascading 가져오기
        master_proforma = ProformaSchedule.objects.filter(
            scenario_id=scenario_id, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if not master_proforma:
            return None

        master = CascadingSchedule.objects.filter(
            scenario_id=scenario_id,
            proforma=master_proforma,
        ).first()

        # 2. 전체 필요 선박 수 (Required Vessels)
        total_slots = master_proforma.declared_count

        # 3. DB에 저장된 실제 선박 배정 데이터 리스트
        saved_details = list(master.details.all()) if master else []

        # 4. 전체 Slot 개수(total_slots)만큼 Row 생성
        rows = []
        base_date = master.proforma_start_etb_date if master else None

        for i in range(total_slots):
            # i번째 주차의 예상 투입일 계산
            row_date = base_date + timedelta(days=i * 7) if base_date else None

            # 저장된 데이터 중 날짜가 일치하는 것이 있는지 확인
            matched = next(
                (d for d in saved_details if d.initial_start_date == row_date), None
            )

            if matched:
                rows.append(
                    {
                        "seq": i + 1,
                        "is_checked": True,
                        "vessel_code": matched.vessel_code,
                        "start_date": matched.initial_start_date.strftime("%Y-%m-%d"),
                    }
                )
            else:
                rows.append(
                    {
                        "seq": i + 1,
                        "is_checked": False,
                        "vessel_code": "",
                        "start_date": row_date.strftime("%Y-%m-%d") if row_date else "",
                    }
                )

        # Scenario의 from/to week 정보 가져오기
        scenario = ScenarioInfo.objects.filter(id=scenario_id).first()

        return {
            "header": {
                "scenario_id": scenario_id,
                "lane_code": lane_code,
                "proforma_name": proforma_name,
                "own_vessel_count": master_proforma.own_vessel_count,
                "from_year_week": scenario.base_year_week if scenario else "",
                "to_year_week": scenario.to_year_week if scenario else "",
                "required_count": total_slots,
            },
            "details": rows,
        }

    def save_cascading(self, post_data, user):
        """화면 입력을 받아 Cascading 테이블(Master & Detail)에 저장"""
        scenario_id = post_data.get("scenario_id")
        lane_code = post_data.get("lane_code")
        proforma_name = post_data.get("proforma_name")
        vessel_codes = post_data.getlist("vessel_code[]")
        vessel_start_dates = post_data.getlist("vessel_start_date[]")

        if not (scenario_id and lane_code and proforma_name):
            raise ValueError(msg.MISSING_REQUIRED_FIELDS_FOR.format(target="Cascading"))

        scenario = ScenarioInfo.objects.get(id=scenario_id)
        master_proforma = ProformaSchedule.objects.filter(
            scenario=scenario, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if not master_proforma:
            raise ValueError(msg.PROFORMA_NOT_FOUND)

        # 1. 기존 데이터 삭제 후 Master 재생성
        CascadingSchedule.objects.filter(
            scenario=scenario, proforma=master_proforma
        ).delete()

        # 첫 번째 vessel_start_date를 proforma_start_etb_date로 사용
        first_row_date_str = (
            vessel_start_dates[0]
            if vessel_start_dates and vessel_start_dates[0]
            else None
        )

        if first_row_date_str:
            proforma_start_etb_date = datetime.strptime(
                first_row_date_str, "%Y-%m-%d"
            ).date()
        else:
            # 기본값: 오늘 날짜
            proforma_start_etb_date = datetime.now().date()

        own_count = len([v for v in vessel_codes if v.strip()])

        cascading = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=master_proforma,
            proforma_start_etb_date=proforma_start_etb_date,
            created_by=user,
            updated_by=user,
        )

        # 2. Detail 데이터 생성
        details_to_create = []
        for v_code, v_date in zip(vessel_codes, vessel_start_dates):
            if v_code.strip() and v_date.strip():
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

        # 3. ProformaSchedule의 own_vessel_count 동기화
        master_proforma.own_vessel_count = own_count
        master_proforma.save(update_fields=["own_vessel_count"])

        return cascading
