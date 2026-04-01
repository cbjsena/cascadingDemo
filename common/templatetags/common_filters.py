from django import template

register = template.Library()


@register.filter
def split(value, sep=","):
    """
    문자열을 sep 기준으로 나누어 리스트로 반환.
    None 이나 빈 문자열이면 빈 리스트.
    """
    if not value:
        return []
    return str(value).split(sep)


@register.filter
def strip(value):
    """
    문자열 양쪽 공백 제거.
    """
    if value is None:
        return ""
    return str(value).strip()
