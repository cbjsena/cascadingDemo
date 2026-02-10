from django.conf import settings
from django.db import models


class CommonModel(models.Model):
    """
    모든 모델의 공통 조상 (Audit Log)
    - 생성일시, 생성자, 수정일시, 수정자
    - 이 모델은 scenario_id를 포함하지 않음 (ScenarioInfo에서도 사용하기 위해)
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name="Created By",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name="Updated By",
    )

    class Meta:
        abstract = True  # DB 테이블 생성 안 함
