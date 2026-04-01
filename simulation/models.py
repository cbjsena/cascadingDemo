from datetime import date

from django.db import IntegrityError, models, transaction
from django.db.models import Max

from common.models import CommonModel
from input_data.models import ScenarioInfo


# Create your models here.
class SimulationStatus(models.TextChoices):
    SNAPSHOTTING = "SNAPSHOTTING", "Started - Snapshotting in Progress"
    SNAPSHOT_DONE = "SNAPSHOT_DONE", "Ended - Snapshotting Completed"
    PENDING = "PENDING", "Pending - Waiting for Simulation to Start"
    RUNNING = "RUNNING", "Running - Simulation in Progress"
    SUCCESS = "SUCCESS", "Success - Simulation Completed Successfully"
    FAILED = "FAILED", "Failed - Simulation Ended with Errors"
    CANCELED = "CANCELED", "Canceled - Simulation Canceled by User"


SEARCH_TYPE_CHOICES = (
    ("EXACT", "MIP"),
    ("EFFICIENT", "Metaheuristic"),
    ("FAST", "Greedy / Rule-based"),
)


class SimulationRun(CommonModel):
    # Auto-incrementing ID (Django standard)
    id = models.AutoField(primary_key=True, verbose_name="Simulation ID")

    # Auto-generated unique code (SCYYYYMMDD_000)
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Simulation Code",
        help_text="Auto-generated unique code (SMYYYYMMDD_NNN)",
        blank=True,
    )

    scenario = models.ForeignKey(ScenarioInfo, on_delete=models.CASCADE)
    algorithm_type = models.CharField(
        max_length=20,
        choices=SEARCH_TYPE_CHOICES,
        default="EXACT",
        verbose_name="Search Type",
    )
    solver_type = models.CharField(
        max_length=20,
        default="cplex",
        verbose_name="Solver Type",
    )
    simulation_status = models.CharField(
        max_length=20, default=SimulationStatus.SNAPSHOTTING
    )
    progress = models.IntegerField(default=0, help_text="진행률 (%)")
    task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Celery Task ID (비동기 작업 추적용)",
    )
    model_start_time = models.DateTimeField(blank=True, null=True)
    model_end_time = models.DateTimeField(blank=True, null=True)
    model_status = models.CharField(
        max_length=50, blank=True, null=True, help_text="모델 실행 상태"
    )
    objective_value = models.FloatField(blank=True, null=True)
    execution_time = models.FloatField(
        blank=True,
        null=True,
        help_text="실행 시간 (초)",
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of what this Simulation tests",
    )

    def __str__(self):
        return f"SimulationExecution {self.id} - {self.scenario.code} - {self.simulation_status}"

    class Meta:
        db_table = "simulation_run"
        verbose_name = "Simulation Execution"
        verbose_name_plural = "Simulation Execution"
        ordering = ["-created_at"]

    @property
    def is_processing(self):
        """
        현재 시스템이 작업 중인 상태인지 확인 (대시보드로 이동해야 함)
        PENDING, SNAPSHOT_DONE, RUNNING
        """
        return self.simulation_status in [
            SimulationStatus.SNAPSHOTTING,
            SimulationStatus.SNAPSHOT_DONE,
            SimulationStatus.PENDING,
            SimulationStatus.RUNNING,
        ]

    @property
    def is_success(self):
        """성공 여부 확인"""
        return self.simulation_status == SimulationStatus.SUCCESS

    @property
    def is_failure(self):
        """실패 여부 확인"""
        return self.simulation_status == SimulationStatus.FAILED

    @property
    def is_running(self):
        """실행 중인지 확인 (Progress Bar 표시용)"""
        return self.simulation_status == SimulationStatus.RUNNING

    @property
    def can_view_result(self):
        """결과 화면을 볼 수 있는 상태인지"""
        return self.simulation_status == SimulationStatus.SUCCESS

    @property
    def can_modify(self):
        """재시작이나 삭제가 가능한 상태인지 (작업 중이 아닌지)"""
        return not self.is_processing

    def save(self, *args, **kwargs):
        """Auto-generate code with concurrent safe retry (format: SMYYYYMMDD_NNN)"""
        if not self.code:

            today_str = date.today().strftime("%Y%m%d")
            prefix = f"SM{today_str}_"

            max_retries = 10  # 동시성 충돌 시 최대 재시도 횟수

            for attempt in range(max_retries):
                last_code = SimulationRun.objects.filter(
                    code__startswith=prefix
                ).aggregate(max_code=Max("code"))["max_code"]

                if last_code:
                    last_num = int(last_code.split("_")[-1])
                    new_num = last_num + 1
                else:
                    new_num = 1

                self.code = f"{prefix}{new_num:03d}"

                try:
                    # 트랜잭션으로 묶어 고유키 충돌 발생 시 롤백 후 재시도
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    break  # 성공적으로 저장되면 루프 탈출

                except IntegrityError as e:
                    if attempt == max_retries - 1:
                        raise Exception(
                            "Failed to generate unique code after multiple attempts. Please try again later."
                        ) from e
                    continue
        else:
            super().save(*args, **kwargs)
