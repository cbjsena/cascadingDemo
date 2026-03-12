"""
Date related utility functions

이 모듈은 시나리오와 BaseWeekPeriod를 기반으로 한 날짜 관련 유틸리티 함수들을 제공합니다.

사용 예제:
    # Bunker, Cost, Vessel 등의 뷰에서 시나리오별 Base Year Month 선택 목록 제공
    from common.utils.date_utils import get_scenario_base_year_month_choices

    # scenario_crud_view 설정에서 사용
    "extra_context": {
        "base_year_month_choices": get_scenario_base_year_month_choices,
    },
"""

from input_data.models import BaseWeekPeriod, ScenarioInfo


def get_base_year_months():
    """BaseWeekPeriod에서 중복 없는 YYYYMM 리스트를 반환한다."""
    return (
        BaseWeekPeriod.objects.values_list("base_year", "base_month")
        .distinct()
        .order_by("base_year", "base_month")
    )


def get_base_year_month_choices():
    """YYYYMM 형태의 선택 목록을 반환한다. BaseWeekPeriod에서 추출."""
    pairs = get_base_year_months()
    return sorted({f"{year}{month:02d}" for year, month in pairs})


def get_scenario_month_range(base_year_week, horizon_months=12):
    """
    base_year_week(YYYYWK)와 horizon_months로 시작 월과 종료 월(YYYYMM) 반환
    Return: (start_month_str, end_month_str) e.g., ("202601", "202612")
    """
    if not base_year_week or len(base_year_week) != 6:
        return None, None

    try:
        year_int = int(base_year_week[:4])
        week_str = base_year_week[4:6]  # "01" 형태의 문자열 그대로 유지

        # 1. DB 조회 시 문자열(week_str) 사용
        start_period = BaseWeekPeriod.objects.filter(
            base_year=year_int, base_week=week_str
        ).first()
        if not start_period:
            return None, None

        start_year = start_period.base_year

        # 2. 산술 연산을 위해 month 문자열("01")을 int(1)로 변환
        start_month_int = int(start_period.base_month)
        start_month_str = f"{start_year:04d}{start_month_int:02d}"

        # 3. 종료 연/월 계산
        total_months = start_month_int + int(horizon_months) - 1
        end_year = start_year + (total_months - 1) // 12
        end_month_int = ((total_months - 1) % 12) + 1

        # 4. 반환 시 다시 "YYYYMM" 포맷으로 조립
        end_month_str = f"{end_year:04d}{end_month_int:02d}"

        return start_month_str, end_month_str
    except (ValueError, TypeError):
        return None, None


def get_scenario_date_range(base_year_week, horizon_months=12):
    """
    base_year_week와 horizon_months로 실제 시작일과 종료일(Date 객체) 반환
    Return: (start_date, end_date)
    """
    if not base_year_week or len(base_year_week) != 6:
        return None, None

    try:
        year_int = base_year_week[:4]
        week_str = base_year_week[4:6]  # "01" 유지

        start_period = BaseWeekPeriod.objects.filter(
            base_year=year_int, base_week=week_str
        ).first()
        if not start_period:
            return None, None

        start_date = start_period.week_start_date
        start_year_int = int(start_period.base_year)
        start_month_int = int(start_period.base_month)

        total_months = start_month_int + int(horizon_months) - 1
        end_year_int = start_year_int + (total_months - 1) // 12
        end_month_int = ((total_months - 1) % 12) + 1

        # DB 조회를 위해 계산된 int(1)을 다시 "01" 문자열로 변환
        end_year_str = f"{end_year_int:04d}"
        end_month_str = f"{end_month_int:02d}"

        # 문자열 정렬('-base_week')도 "01", "02" 형태이므로 정상적으로 가장 큰 값을 가져옵니다.
        end_period = (
            BaseWeekPeriod.objects.filter(
                base_year=end_year_str, base_month=end_month_str
            )
            .order_by("-base_week")
            .first()
        )

        if not end_period:
            return None, None

        return start_date, end_period.week_end_date
    except (ValueError, TypeError):
        return None, None


def get_timeline_weeks(base_year_week, horizon_months=12):
    """
    UI 렌더링(Gantt 차트 등)용 타임라인 주차 목록 반환
    Return: List of Dicts [{"label": "01", "start_date": Date, ...}]
    """
    weeks = []
    start_date, end_date = get_scenario_date_range(base_year_week, horizon_months)

    if not (start_date and end_date):
        return weeks

    qs = BaseWeekPeriod.objects.filter(
        week_start_date__gte=start_date, week_end_date__lte=end_date
    ).order_by("week_start_date")

    for i, period in enumerate(qs):
        # 모델의 base_week가 "01" 문자열일 수 있으므로 :02d 대신 zfill(2)을 사용하여 에러 방지
        week_str = str(period.base_week).zfill(2)

        weeks.append(
            {
                "label": week_str,
                "year": period.base_year,
                "week_num": period.base_week,  # 원본 데이터 유지
                "start_date": period.week_start_date,
                "index": i,
            }
        )
    return weeks


def get_scenario_base_year_month_choices(scenario_id=None):
    """시나리오별 Base Year Month 선택 목록을 반환한다.

    Args:
        scenario_id (str|int, optional): 시나리오 ID. None이면 전체 BaseWeekPeriod 반환.

    Returns:
        list[str]: YYYYMM 형태의 문자열 목록 (예: ['202601', '202602', ...])

    Description:
        시나리오가 선택된 경우, 해당 시나리오의 base_year_week부터
        planning_horizon_months 기간 내의 BaseWeekPeriod만 반환한다.

        시나리오 미선택이거나 시나리오 정보가 없는 경우, 전체 BaseWeekPeriod를 반환한다.

    Usage:
        # _crud_base.py에서 extra_context 함수로 자동 호출됨
        # scenario_id 파라미터는 자동으로 전달됨
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
        }
    """
    if not scenario_id:
        return get_base_year_month_choices()

    try:
        scenario = ScenarioInfo.objects.get(id=scenario_id)

        if not scenario.base_year_week:
            return get_base_year_month_choices()

        # base_year_week 파싱 (예: "202610" -> year=2026, week=10)
        base_year = int(scenario.base_year_week[:4])
        base_week = scenario.base_year_week[4:]

        # 시작 주차에 해당하는 base_month 조회
        base_month_result = (
            BaseWeekPeriod.objects.filter(base_year=base_year, base_week=base_week)
            .values_list("base_month", flat=True)
            .first()
        )

        if not base_month_result:
            return get_base_year_month_choices()

        base_month = base_month_result
        planning_months = scenario.planning_horizon_months or 12

        # planning_months를 고려한 end_year, end_month 계산
        end_month = base_month + planning_months
        end_year = base_year

        # 년도 경계 처리 (12월 초과 시 다음 년도로)
        while end_month > 12:
            end_month -= 12
            end_year += 1

        # BaseWeekPeriod에서 base_year/base_month부터 end_year/end_month까지 범위 조회
        from django.db.models import Q

        if end_year > base_year:
            # 여러 년도에 걸쳐 있는 경우
            # 시작년도의 시작월부터
            start_condition = Q(base_year=base_year, base_month__gte=base_month)
            # 중간년도들 (전체)
            middle_condition = Q(base_year__gt=base_year, base_year__lt=end_year)
            # 종료년도의 종료월까지
            end_condition = Q(base_year=end_year, base_month__lte=end_month)

            filter_condition = start_condition | middle_condition | end_condition
        else:
            # 같은 년도 내에서 월 범위
            filter_condition = Q(
                base_year=base_year,
                base_month__gte=base_month,
                base_month__lte=end_month,
            )

        pairs = (
            BaseWeekPeriod.objects.filter(filter_condition)
            .values_list("base_year", "base_month")
            .distinct()
            .order_by("base_year", "base_month")
        )

        return sorted({f"{year}{month:02d}" for year, month in pairs})

    except (ScenarioInfo.DoesNotExist, ValueError, AttributeError):
        # 에러 발생 시 전체 목록 반환
        return get_base_year_month_choices()
