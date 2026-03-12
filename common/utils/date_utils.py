"""
Date related utility functions
이 모듈은 시나리오와 BaseWeekPeriod를 기반으로 한 날짜 관련 유틸리티 함수들을 제공합니다.
"""

from input_data.models import BaseWeekPeriod, ScenarioInfo
from django.db.models import Q


def get_base_year_months():
    """BaseWeekPeriod에서 중복 없는 YYYYMM 리스트를 반환한다."""
    return (
        BaseWeekPeriod.objects.values_list("base_year", "base_month")
        .distinct()
        .order_by("base_year", "base_month")
    )


def get_base_year_month_choices():
    """YYYYMM 형태의 선택 목록을 반환한다."""
    pairs = get_base_year_months()
    return sorted({f"{year}{str(month).zfill(2)}" for year, month in pairs})


def get_scenario_month_range(base_year_week, horizon_months=12):
    """base_year_week(YYYYWK)와 horizon_months로 시작 월과 종료 월(YYYYMM) 반환"""
    if not base_year_week or len(base_year_week) != 6:
        return None, None

    try:
        year_str = base_year_week[:4]
        week_str = base_year_week[4:6]

        start_period = BaseWeekPeriod.objects.filter(
            base_year=year_str, base_week=week_str
        ).first()
        if not start_period:
            return None, None

        start_year_int = int(start_period.base_year)
        start_month_int = int(start_period.base_month)

        start_month_str = f"{start_year_int:04d}{start_month_int:02d}"

        total_months = start_month_int + int(horizon_months) - 1
        end_year_int = start_year_int + (total_months - 1) // 12
        end_month_int = ((total_months - 1) % 12) + 1

        end_month_str = f"{end_year_int:04d}{end_month_int:02d}"

        return start_month_str, end_month_str
    except (ValueError, TypeError):
        return None, None


def get_scenario_date_range(base_year_week, horizon_months=12):
    """base_year_week와 horizon_months로 실제 시작일과 종료일(Date 객체) 반환"""
    if not base_year_week or len(base_year_week) != 6:
        return None, None

    try:
        year_str = base_year_week[:4]
        week_str = base_year_week[4:6]

        start_period = BaseWeekPeriod.objects.filter(
            base_year=year_str, base_week=week_str
        ).first()
        if not start_period:
            return None, None

        start_date = start_period.week_start_date
        start_year_int = int(start_period.base_year)
        start_month_int = int(start_period.base_month)

        total_months = start_month_int + int(horizon_months) - 1
        end_year_int = start_year_int + (total_months - 1) // 12
        end_month_int = ((total_months - 1) % 12) + 1

        end_year_str = f"{end_year_int:04d}"
        end_month_str = f"{end_month_int:02d}"

        # 문자열 정렬이므로 '01', '02' 형식에서 가장 큰 주차를 안전하게 가져옴
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
    """UI 렌더링용 타임라인 주차 목록 반환"""
    weeks = []
    start_date, end_date = get_scenario_date_range(base_year_week, horizon_months)

    if not (start_date and end_date):
        return weeks

    qs = BaseWeekPeriod.objects.filter(
        week_start_date__gte=start_date, week_end_date__lte=end_date
    ).order_by("week_start_date")

    for i, period in enumerate(qs):
        week_str = str(period.base_week).zfill(2)
        weeks.append(
            {
                "label": week_str,
                "year": period.base_year,
                "week_num": period.base_week,
                "start_date": period.week_start_date,
                "index": i,
            }
        )
    return weeks


def get_scenario_base_year_month_choices(scenario_id=None):
    """시나리오별 Base Year Month 선택 목록을 반환한다."""
    if not scenario_id:
        return get_base_year_month_choices()

    try:
        scenario = ScenarioInfo.objects.get(id=scenario_id)

        if not scenario.base_year_week:
            return get_base_year_month_choices()

        base_year_str = scenario.base_year_week[:4]
        base_week_str = scenario.base_year_week[4:6]

        base_month_result = (
            BaseWeekPeriod.objects.filter(base_year=base_year_str, base_week=base_week_str)
            .values_list("base_month", flat=True)
            .first()
        )

        if not base_month_result:
            return get_base_year_month_choices()

        # [수정됨] 산술 연산을 위해 int로 변환
        base_year_int = int(base_year_str)
        base_month_int = int(base_month_result)
        planning_months = int(scenario.planning_horizon_months or 12)

        end_month_int = base_month_int + planning_months - 1
        end_year_int = base_year_int

        while end_month_int > 12:
            end_month_int -= 12
            end_year_int += 1

        # [수정됨] 쿼리를 위해 다시 0 패딩된 문자열로 변환
        end_year_str = f"{end_year_int:04d}"
        end_month_str = f"{end_month_int:02d}"
        start_month_str = f"{base_month_int:02d}"

        # CharField는 0이 채워져 있으므로 크기 비교(gte, lte)가 숫자의 대소와 완벽히 일치함
        if end_year_int > base_year_int:
            start_condition = Q(base_year=base_year_str, base_month__gte=start_month_str)
            middle_condition = Q(base_year__gt=base_year_str, base_year__lt=end_year_str)
            end_condition = Q(base_year=end_year_str, base_month__lte=end_month_str)
            filter_condition = start_condition | middle_condition | end_condition
        else:
            filter_condition = Q(
                base_year=base_year_str,
                base_month__gte=start_month_str,
                base_month__lte=end_month_str,
            )

        pairs = (
            BaseWeekPeriod.objects.filter(filter_condition)
            .values_list("base_year", "base_month")
            .distinct()
            .order_by("base_year", "base_month")
        )

        return sorted({f"{year}{str(month).zfill(2)}" for year, month in pairs})

    except (ScenarioInfo.DoesNotExist, ValueError, AttributeError):
        return get_base_year_month_choices()