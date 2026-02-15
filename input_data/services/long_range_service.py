from django.db import transaction


class LongRangeService:
    """
    Long Range Schedule 비즈니스 로직
    """

    @transaction.atomic
    def create_lrs(self, post_data, user):
        """
        화면에서 입력받은 정보를 바탕으로 LRS 데이터를 생성
        """
        # Todo scenario_id, proforma_name, apply_start_date, apply_end_date
        # 1. Header Info
        # scenario_id = post_data.get("scenario_id")
        lane_code = post_data.get("lane_code")
        # proforma_name = post_data.get("proforma_name")

        # apply_start_date = post_data.get("apply_start_date")  # LRS 전체 시작일
        # apply_end_date = post_data.get("apply_end_date")  # LRS 전체 종료일
        own_vessel_count = int(post_data.get("own_vessel_count", 0))

        # 2. Grid Info (Arrays)
        vessel_names = post_data.getlist("vessel_name[]")
        vessel_start_dates = post_data.getlist("vessel_start_date[]")

        # 3. Validation
        if not vessel_names:
            raise ValueError("No vessel data provided.")

        # TODO: Implement actual LRS Generation Logic
        # 입력된 기간(apply_start ~ apply_end) 동안,
        # 각 선박(vessel_names)별로 Proforma 스케줄을 반복(Loop) 생성

        print(f"Generating LRS for {lane_code} ({own_vessel_count} Own Vessels)...")
        for i, v_name in enumerate(vessel_names):
            v_start = vessel_start_dates[i]
            if v_name:
                print(f" - Vessel: {v_name}, Start: {v_start}")
                # Logic implementation here...
