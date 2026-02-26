"""
숫자 처리 관련 유틸리티 함수들
"""

import decimal
from decimal import ROUND_HALF_UP, Decimal


def safe_round(value, digits=1):
    """
    숫자 값을 안전하게 반올림하는 함수

    Args:
        value: 반올림할 값 (None, int, float, str, Decimal 등)
        digits: 소수점 자릿수 (기본값: 1)

    Returns:
        float: 반올림된 값, None인 경우 0.0 반환

    Examples:
        safe_round(None) -> 0.0
        safe_round(2.555, 1) -> 2.6
        safe_round("3.14159", 2) -> 3.14
        safe_round(Decimal("5.55"), 1) -> 5.6
    """
    if value is None or value == "" or value == "null":
        return 0.0

    try:
        # Decimal을 사용하여 정확한 반올림 처리
        decimal_value = Decimal(str(value))
        # 소수점 자릿수에 맞는 quantize 패턴 생성
        quantize_pattern = "0." + "0" * digits if digits > 0 else "1"
        rounded_decimal = decimal_value.quantize(
            Decimal(quantize_pattern), rounding=ROUND_HALF_UP
        )
        return float(rounded_decimal)
    except (TypeError, ValueError, decimal.InvalidOperation):
        return 0.0


def safe_float(value, default=0.0):
    """
    값을 안전하게 float로 변환하는 함수

    Args:
        value: 변환할 값
        default: 변환 실패시 기본값 (기본값: 0.0)

    Returns:
        float: 변환된 값 또는 기본값
    """
    if value is None or value == "" or value == "null":
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    """
    값을 안전하게 int로 변환하는 함수

    Args:
        value: 변환할 값
        default: 변환 실패시 기본값 (기본값: 0)

    Returns:
        int: 변환된 값 또는 기본값
    """
    if value is None or value == "" or value == "null":
        return default

    try:
        # float로 먼저 변환 후 int로 변환 (소수점이 있는 문자열 처리)
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_sum(values, safe_func=safe_float):
    """
    리스트의 값들을 안전하게 합산하는 함수

    Args:
        values: 합산할 값들의 리스트 또는 제너레이터
        safe_func: 안전 변환 함수 (기본값: safe_float)

    Returns:
        변환된 값들의 합계
    """
    total = 0
    for value in values:
        total += safe_func(value)
    return total
