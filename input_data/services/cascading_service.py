from datetime import datetime, timedelta

from common import messages as msg
from input_data.models import (
    CascadingVesselPosition,
    ProformaSchedule,
    ScenarioInfo,
)


class CascadingService:
    """
    Cascading Vessel Position 화면 데이터 조회 및 DB 저장 전담 서비스
    """

    def get_cascading_data(self, scenario_id, lane_code, proforma_name):
        """[Edit 모드용] Cascading 데이터를 불러옵니다."""
        # 1. Master Proforma 가져오기
        master_proforma = ProformaSchedule.objects.filter(
            scenario_id=scenario_id, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if not master_proforma:
            return None

        # 2. 전체 필요 선박 수 (Required Vessels)
        total_slots = master_proforma.declared_count

        # 3. DB에 저장된 실제 선박 배정 데이터 리스트
        saved_positions = list(
            CascadingVesselPosition.objects.filter(
                scenario_id=scenario_id, proforma=master_proforma
            ).order_by("vessel_position")
        )

        # Scenario의 from/to week 정보 가져오기
        scenario = ScenarioInfo.objects.filter(id=scenario_id).first()

        # 4. 첫 번째 position의 날짜를 기준으로 base_date 계산
        base_date = None
        if saved_positions:
            first_pos = next(
                (p for p in saved_positions if p.vessel_position == 1), None
            )
            if first_pos:
                base_date = first_pos.vessel_position_date

        # 5. 전체 Slot 개수(total_slots)만큼 Row 생성
        rows = []
        for i in range(total_slots):
            position_num = i + 1
            # i번째 주차의 예상 투입일 계산
            row_date = base_date + timedelta(days=i * 7) if base_date else None

            # 저장된 데이터 중 position이 일치하는 것이 있는지 확인
            matched = next(
                (p for p in saved_positions if p.vessel_position == position_num), None
            )

            if matched:
                rows.append(
                    {
                        "seq": position_num,
                        "is_checked": True,
                        "vessel_code": matched.vessel_code,
                        "start_date": matched.vessel_position_date.strftime("%Y-%m-%d"),
                    }
                )
            else:
                rows.append(
                    {
                        "seq": position_num,
                        "is_checked": False,
                        "vessel_code": "",
                        "start_date": row_date.strftime("%Y-%m-%d") if row_date else "",
                    }
                )

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
        """화면 입력을 받아 CascadingVesselPosition 테이블에 저장"""
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

        # 1. 기존 데이터 삭제
        CascadingVesselPosition.objects.filter(
            scenario=scenario, proforma=master_proforma
        ).delete()

        # 2. 새 Position 데이터 생성
        positions_to_create = []
        position_num = 0
        for i, (v_code, v_date) in enumerate(zip(vessel_codes, vessel_start_dates)):
            if v_code.strip() and v_date.strip():
                position_num += 1
                positions_to_create.append(
                    CascadingVesselPosition(
                        scenario=scenario,
                        proforma=master_proforma,
                        vessel_code=v_code,
                        vessel_position=position_num,
                        vessel_position_date=datetime.strptime(
                            v_date, "%Y-%m-%d"
                        ).date(),
                        created_by=user,
                        updated_by=user,
                    )
                )

        if positions_to_create:
            CascadingVesselPosition.objects.bulk_create(positions_to_create)

        # 3. ProformaSchedule의 own_vessel_count 동기화
        own_count = len(positions_to_create)
        master_proforma.own_vessel_count = own_count
        master_proforma.save(update_fields=["own_vessel_count"])

        return positions_to_create
