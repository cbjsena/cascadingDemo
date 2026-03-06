from django.db import models

from common.models import CommonModel

SCENARIO_STATUS_CODE = (
    ("DRAFT", "Draft - Work in Progress"),
    ("ACTIVE", "Active - Ready for Analysis"),
    ("ARCHIVED", "Archived - Completed Analysis"),
    ("BASELINE", "Baseline - Reference Scenario"),
)

SCENARIO_TYPE_CHOICES = (
    ("BASELINE", "Baseline Scenario"),
    ("WHAT_IF", "What-If Analysis"),
    ("OPTIMIZATION", "Optimization Study"),
    ("SENSITIVITY", "Sensitivity Analysis"),
    ("COMPARISON", "Scenario Comparison"),
)
OWN_TYPE_CHOICES = (("O", "Own"), ("C", "Chartered"))
DIRECTION_CHOICES = (("E", "East"), ("W", "West"), ("S", "South"), ("N", "North"))
SCHEDULE_CHANGE_STATUS_CODE_CHOICES = (
    ("A", "Ad hoc Call"),
    ("I", "Phase In"),
    ("L", "Vessel Slide"),
    ("O", "Phase Out"),
    ("S", "Port Omission"),
    ("R", "Port Call Swap"),
)
FULL_EMPTY_CHOICES = (("F", "Full"), ("E", "Empty"))
BUNKER_TYPE_CHOICES = (("LSFO", "Low Sulphur Fuel Oil"), ("MGO", "Marine Gas Oil"))
TURN_PORT_INFO_CD = (("Y", "Y"), ("N", "N"))
DEPLOYMENT_TYPE_CHOICES = (
    ("I", "Include"),
    ("E", "Exclude"),
    # ("P", "Preferred"),
    # ("S", "Substitute"),
)


# ==========================================
# [Main] Scenario Info
# ==========================================
class ScenarioInfo(CommonModel):
    # Auto-incrementing ID (Django standard)
    id = models.AutoField(primary_key=True, verbose_name="Scenario ID")

    # Auto-generated unique code (SCYYYYMMDD_000)
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Scenario Code",
        help_text="Auto-generated unique code (SCYYYYMMDD_NNN)",
        blank=True,
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of what this scenario tests",
    )

    # Simulation-specific fields
    scenario_type = models.CharField(
        max_length=20,
        choices=SCENARIO_TYPE_CHOICES,
        default="WHAT_IF",
        verbose_name="Scenario Type",
    )
    base_scenario = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Base Scenario",
        help_text="Reference scenario for comparison",
    )

    # Planning period
    base_year_week = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        verbose_name="Base Year-Week / YYYYWK",
        help_text="Planning period start week (e.g., 202610)",
    )
    planning_horizon_months = models.PositiveIntegerField(
        default=12,
        verbose_name="Planning Horizon (Months)",
        help_text="How many months ahead to simulate",
    )

    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=SCENARIO_STATUS_CODE,
        default="DRAFT",
        verbose_name="Scenario Status",
    )
    tags = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Tags",
        help_text="Comma-separated tags for categorization (e.g., capacity-test, route-optimization)",
    )

    # Analysis results cache
    last_calculated = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Calculated",
        help_text="When this scenario was last fully calculated",
    )
    calculation_status = models.CharField(
        max_length=20,
        choices=(
            ("PENDING", "Pending Calculation"),
            ("CALCULATING", "Currently Calculating"),
            ("COMPLETED", "Calculation Complete"),
            ("ERROR", "Calculation Error"),
        ),
        default="PENDING",
        verbose_name="Calculation Status",
    )

    class Meta:
        verbose_name = "Scenario Info"
        verbose_name_plural = "Simulation Scenarios"
        db_table = "sce_scenario_info"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} (ID: {self.id})"

    def save(self, *args, **kwargs):
        """Auto-generate code if not provided (format: SCYYYYMMDD_NNN)"""
        if not self.code:
            from datetime import date

            from django.db.models import Max

            today_str = date.today().strftime("%Y%m%d")
            prefix = f"SC{today_str}_"

            # 오늘 날짜로 생성된 시나리오 중 가장 큰 번호 찾기
            last_code = ScenarioInfo.objects.filter(code__startswith=prefix).aggregate(
                max_code=Max("code")
            )["max_code"]

            if last_code:
                # 기존 번호에서 숫자 추출 후 +1
                last_num = int(last_code.split("_")[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.code = f"{prefix}{new_num:03d}"

        super().save(*args, **kwargs)

    @property
    def is_baseline(self):
        """Check if this is a baseline scenario"""
        return self.scenario_type == "BASELINE"

    @property
    def to_year_week(self):
        """Calculate end week based on base_year_week and planning_horizon_months"""
        if not self.base_year_week or not self.planning_horizon_months:
            return None

        try:
            # base_year_week format: YYYYWK (e.g., 202610)
            year = int(self.base_year_week[:4])
            week = int(self.base_year_week[4:])

            # planning_horizon_months를 주차로 변환 (1개월 ≈ 4.33주)
            weeks_to_add = int(self.planning_horizon_months * 4.33)

            # 종료 주차 계산
            end_week = week + weeks_to_add
            end_year = year

            # 연도 넘김 처리 (52주 기준)
            while end_week > 52:
                end_week -= 52
                end_year += 1

            return f"{end_year}{end_week:02d}"
        except (ValueError, TypeError):
            return None

    @property
    def tag_list(self):
        """Return tags as a list"""
        return (
            [tag.strip() for tag in self.tags.split(",") if tag.strip()]
            if self.tags
            else []
        )

    def get_comparison_scenarios(self):
        """Get scenarios that use this as a base for comparison"""
        return ScenarioInfo.objects.filter(base_scenario=self)


# ==========================================
# [Abstract] Scenario FK Mixin
# ==========================================
class ScenarioBaseModel(CommonModel):
    """시나리오 테이블용 공통 모델 (FK + Audit)"""

    scenario = models.ForeignKey(
        ScenarioInfo,
        on_delete=models.CASCADE,
        verbose_name="Scenario ID",
        related_name="%(class)s_set",
    )

    class Meta:
        abstract = True


# ==========================================
# Group 1: Schedule
# ==========================================
# 1. Proforma Schedule
class BaseProformaSchedule(models.Model):
    """[BASE] 기준 Proforma Schedule"""

    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    proforma_name = models.CharField(
        max_length=30, verbose_name="Proforma Name / 4 numeric digits"
    )
    effective_from_date = models.DateTimeField(
        verbose_name="Effective start date of the proforma."
    )
    effective_to_date = models.DateTimeField(
        null=True, verbose_name="Effective end date of the proforma."
    )
    duration = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Total number of days from the ETB of the first port to the ETB of the last port",
    )
    declared_capacity = models.CharField(
        max_length=5,
        verbose_name="Declared vessel capacity (TEU) for the lane, Currently equal to vessel_capacity",
    )
    declared_count = models.IntegerField(
        verbose_name="Declared number of vessels for the lane"
    )
    own_vessel_count = models.IntegerField(
        default=0,
        verbose_name="Number of own vessels assigned via cascading",
    )
    direction = models.CharField(
        max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E, S, N}"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    calling_port_indicator = models.CharField(
        max_length=2,
        verbose_name="Port call order for each direction and port within the lane",
    )
    calling_port_seq = models.IntegerField(
        verbose_name="Port call sequence within the lane"
    )
    turn_port_info_code = models.CharField(
        max_length=3,
        choices=TURN_PORT_INFO_CD,
        default="N",
        verbose_name="Turning Port Indicator (Y/N) / Y: Create Virtual Port ",
    )
    pilot_in_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Time from outer port to berth (Hour)",
        default=3,
    )
    etb_day_number = models.IntegerField(
        verbose_name="Total number of days from the first port ETB to this ETB"
    )
    etb_day_code = models.CharField(max_length=3, verbose_name="Day of week for ETB")
    etb_day_time = models.CharField(max_length=4, verbose_name="ETB time (HHMM)")
    actual_work_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Actual working time at the berth (hours)",
        default=30,
    )
    etd_day_number = models.IntegerField(
        null=True,
        verbose_name="Total number of days from the first port ETB to this ETD",
    )
    etd_day_code = models.CharField(
        null=True, max_length=3, verbose_name="Day of week for ETD"
    )
    etd_day_time = models.CharField(
        null=True, max_length=4, verbose_name="ETD time (HHMM)"
    )
    pilot_out_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Time from berth to outer port  (Hour)",
        default=3,
    )

    link_distance = models.IntegerField(
        null=True, verbose_name="Distance to Next Port (NM)", default=0
    )
    link_eca_distance = models.IntegerField(
        null=True, verbose_name="ECA Distance to Next Port (NM)", default=0
    )
    link_speed = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Average Speed to Next Port (knots)",
    )
    sea_time_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Sea Time (hours), Next port ETB − Current port ETD − Current port Pilot Out + Next port Pilot In",
    )
    terminal_code = models.CharField(
        max_length=10,
        verbose_name="Terminal Code (Port Code + 2-digit number, e.g., KRPUS01)",
    )

    # 표준 데이터는 scenario_id, created_by, updated_by 없음
    class Meta:
        verbose_name = "Base Proforma Schedule"
        db_table = "base_schedule_proforma"
        unique_together = (
            (
                "lane_code",
                "proforma_name",
                "direction",
                "port_code",
                "calling_port_indicator",
            ),
        )

    def __str__(self):
        return f"[BASE] {self.lane_code} - {self.proforma_name}"


class ProformaSchedule(ScenarioBaseModel):
    """시나리오 복사 시 분리되는 헤더 정보"""

    scenario = models.ForeignKey(
        "ScenarioInfo", on_delete=models.CASCADE, db_column="scenario_id"
    )

    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    proforma_name = models.CharField(
        max_length=30, verbose_name="Proforma Name / 4 numeric digits"
    )
    effective_from_date = models.DateTimeField(
        verbose_name="Effective start date of the proforma."
    )
    effective_to_date = models.DateTimeField(
        null=True, verbose_name="Effective end date of the proforma."
    )
    duration = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Total number of days from the ETB of the first port to the ETB of the last port",
    )
    declared_capacity = models.CharField(
        max_length=5,
        verbose_name="Declared vessel capacity (TEU) for the lane, Currently equal to vessel_capacity",
    )
    declared_count = models.IntegerField(
        verbose_name="Declared number of vessels for the lane"
    )
    own_vessel_count = models.IntegerField(
        default=0,
        verbose_name="Number of own vessels assigned via cascading",
    )

    class Meta:
        db_table = "sce_schedule_proforma"
        unique_together = ("scenario", "lane_code", "proforma_name")

    def __str__(self):
        return f"[{self.scenario.id}] {self.lane_code} - {self.proforma_name}"


class ProformaScheduleDetail(CommonModel):
    """시나리오 복사 시 분리되는 기항지 상세 정보"""

    proforma = models.ForeignKey(
        ProformaSchedule,
        on_delete=models.CASCADE,
        related_name="details",
        db_column="proforma_id",
        verbose_name="Proforma Master ID",
    )

    direction = models.CharField(
        max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E, S, N}"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    calling_port_indicator = models.CharField(
        max_length=2,
        verbose_name="Port call order for each direction and port within the lane",
    )
    calling_port_seq = models.IntegerField(
        verbose_name="Port call sequence within the lane"
    )
    turn_port_info_code = models.CharField(
        max_length=3,
        choices=TURN_PORT_INFO_CD,
        default="N",
        verbose_name="Turning Port Indicator (Y/N) / Y: Create Virtual Port ",
    )
    pilot_in_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Time from outer port to berth (Hour)",
        default=3,
    )
    etb_day_number = models.IntegerField(
        verbose_name="Total number of days from the first port ETB to this ETB"
    )
    etb_day_code = models.CharField(max_length=3, verbose_name="Day of week for ETB")
    etb_day_time = models.CharField(max_length=4, verbose_name="ETB time (HHMM)")
    actual_work_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Actual working time at the berth (hours)",
        default=30,
    )
    etd_day_number = models.IntegerField(
        null=True,
        verbose_name="Total number of days from the first port ETB to this ETD",
    )
    etd_day_code = models.CharField(
        null=True, max_length=3, verbose_name="Day of week for ETD"
    )
    etd_day_time = models.CharField(
        null=True, max_length=4, verbose_name="ETD time (HHMM)"
    )
    pilot_out_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Time from berth to outer port  (Hour)",
        default=3,
    )

    link_distance = models.IntegerField(
        null=True, verbose_name="Distance to Next Port (NM)", default=0
    )
    link_eca_distance = models.IntegerField(
        null=True, verbose_name="ECA Distance to Next Port (NM)", default=0
    )
    link_speed = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Average Speed to Next Port (knots)",
    )
    sea_time_hours = models.DecimalField(
        null=True,
        max_digits=8,
        decimal_places=3,
        verbose_name="Sea Time (hours), Next port ETB − Current port ETD − Current port Pilot Out + Next port Pilot In",
    )
    terminal_code = models.CharField(
        max_length=10,
        verbose_name="Terminal Code (Port Code + 2-digit number, e.g., KRPUS01)",
    )

    class Meta:
        db_table = "sce_schedule_proforma_detail"
        unique_together = (
            "proforma",
            "direction",
            "port_code",
            "calling_port_indicator",
        )


# 2. Cascading


class BaseCascadingSchedule(models.Model):
    """[BASE] 기준 Cascading Schedule - Flat Structure for CSV Import"""

    lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
    proforma_name = models.CharField(max_length=30, verbose_name="Proforma Name")
    vessel_code = models.CharField(max_length=20, verbose_name="Vessel Code")
    initial_start_date = models.DateField(verbose_name="Initial Start Date")

    class Meta:
        db_table = "base_schedule_cascading"
        verbose_name = "Base Cascading Schedule"
        verbose_name_plural = "Base Cascading Schedules"
        unique_together = (
            (
                "lane_code",
                "proforma_name",
                "vessel_code",
            ),
        )

    def __str__(self):
        return f"{self.lane_code} - {self.proforma_name} - {self.vessel_code}"


class CascadingSchedule(ScenarioBaseModel):
    """Cascading Schedule 헤더 (Proforma 1 : N Cascading)"""

    scenario = models.ForeignKey(
        "ScenarioInfo", on_delete=models.CASCADE, db_column="scenario_id"
    )
    proforma = models.ForeignKey(
        ProformaSchedule,
        on_delete=models.CASCADE,
        related_name="cascading",
        db_column="proforma_id",
        verbose_name="Proforma Master ID",
    )

    proforma_start_etb_date = models.DateField(
        verbose_name="ETB date of the first vessel at the first port in proforma"
    )

    class Meta:
        db_table = "sce_schedule_cascading"
        unique_together = ("scenario", "proforma")

    def __str__(self):
        return f"[{self.scenario.id}] {self.proforma.proforma_name}"


class CascadingScheduleDetail(CommonModel):
    """Cascading Schedule 상세 (선박 목록)"""

    cascading = models.ForeignKey(
        CascadingSchedule,
        on_delete=models.CASCADE,
        related_name="details",
        db_column="cascading_id",
        verbose_name="Cascading Master ID",
    )

    vessel_code = models.CharField(max_length=20, verbose_name="Vessel Code")
    initial_start_date = models.DateField(verbose_name="Initial Start Date")

    class Meta:
        db_table = "sce_schedule_cascading_detail"
        # Cascading ID + Vessel Code 조합은 유일해야 함
        unique_together = ("cascading", "vessel_code")

    def __str__(self):
        return f"{self.cascading} - {self.vessel_code}"


# 3. Long Range Schedule
class AbsLongRangeSchedule(models.Model):
    """Long Range Schedule 데이터 필드 (추상)"""

    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    vessel_code = models.CharField(
        max_length=10, verbose_name="Vessel Code / 4 alphanum"
    )
    voyage_number = models.CharField(
        max_length=20, verbose_name="Voyage Number / 4 numeric digits"
    )
    direction = models.CharField(
        max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E, S, N}"
    )
    start_port_berthing_year_week = models.CharField(
        max_length=6, verbose_name="Start Port Berthing Year Week"
    )
    proforma_name = models.CharField(
        max_length=30, verbose_name="Proforma Name / 4 numeric digits"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    calling_port_indicator = models.CharField(
        max_length=2, verbose_name="Port call order per port within a VVD"
    )
    calling_port_seq = models.IntegerField(
        verbose_name="Port call sequence within the VVD"
    )
    schedule_change_status_code = models.CharField(
        max_length=1,
        choices=SCHEDULE_CHANGE_STATUS_CODE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Schedule Change Status {A: Ad hoc Call, I: Phase In, L: Vessel Slide, O: Phase Out, S: Port Omission, R: Port Call Swap}",
    )
    eta = models.DateTimeField(
        null=True, blank=True, verbose_name="Estimated Time of Arrival"
    )
    etb = models.DateTimeField(
        null=True, blank=True, verbose_name="Estimated Time of Berthing"
    )
    etd = models.DateTimeField(
        null=True, blank=True, verbose_name="Estimated Time of Departure"
    )
    terminal_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="Terminal Code (Port Code + 2-digit number, e.g., KRPUS01)",
    )

    class Meta:
        abstract = True


class BaseLongRangeSchedule(AbsLongRangeSchedule):
    """[BASE] 기준 Long Range Schedule"""

    class Meta:
        verbose_name = "Base Long Range Schedule"
        db_table = "base_schedule_long_range"
        unique_together = (
            (
                "lane_code",
                "vessel_code",
                "voyage_number",
                "direction",
                "port_code",
                "calling_port_indicator",
            ),
        )


class LongRangeSchedule(AbsLongRangeSchedule, ScenarioBaseModel):
    """[SCE] 시나리오 Long Range Schedule"""

    class Meta:
        verbose_name = "Long Range Schedule"
        db_table = "sce_schedule_long_range"
        unique_together = (
            (
                "scenario",
                "lane_code",
                "vessel_code",
                "voyage_number",
                "direction",
                "port_code",
                "calling_port_indicator",
            ),
        )

    def __str__(self):
        return f"{self.lane_code} - {self.vessel_code}{self.voyage_number}{self.direction} - {self.port_code} ({self.calling_port_indicator})"


# ==========================================
# Group 2: Vessel
# ==========================================
# 3. Vessel Info
class AbsVesselInfo(models.Model):
    """Vessel Info 데이터 필드 (추상)"""

    vessel_code = models.CharField(
        max_length=10, verbose_name="Vessel Code / 4 alphanum"
    )
    vessel_name = models.CharField(max_length=50, verbose_name="Vessel Name")
    # nominal_capacity = models.IntegerField(verbose_name="Nominal Capacity")
    own_yn = models.CharField(
        max_length=1,
        choices=OWN_TYPE_CHOICES,
        verbose_name="Distinguish if it's own {O: Own, C: Charter}",
    )
    delivery_port_code = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="Delivery Port Code"
    )
    delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Delivery Date"
    )
    redelivery_port_code = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="Redelivery Port Code"
    )
    redelivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Redelivery Date"
    )
    next_dock_port_code = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="Next Dock Port Code"
    )
    next_dock_in_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Next Dock In Date"
    )
    next_dock_out_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Next Dock Out Date"
    )
    built_port_code = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="Built Port Code"
    )
    built_date = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Built Date"
    )

    class Meta:
        abstract = True


class BaseVesselInfo(AbsVesselInfo):
    """[BASE] 기준 Vessel Info"""

    class Meta:
        verbose_name = "Base Vessel Info and Charter, Dock, Built of vessel "
        db_table = "base_vessel_info"
        unique_together = ("vessel_code",)

    def __str__(self):
        return f"[BASE] {self.vessel_code}"


class VesselInfo(AbsVesselInfo, ScenarioBaseModel):
    """[SCE] 시나리오 Vessel Info"""

    class Meta:
        verbose_name = "Vessel Info and Charter, Dock, Built of vessel "
        db_table = "sce_vessel_info"
        unique_together = (
            "scenario",
            "vessel_code",
        )

    def __str__(self):
        return f"[{self.scenario.id}] {self.vessel_code}"


# 4. Charter Cost
class AbsCharterCost(models.Model):
    """Charter Cost 데이터 필드 (추상)"""

    vessel_code = models.CharField(
        max_length=4, verbose_name="Vessel Code / 4 alphanum"
    )
    # currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
    hire_from_date = models.DateTimeField(
        verbose_name="From date for applying the hire cost"
    )
    hire_to_date = models.DateTimeField(
        verbose_name="To date for applying the hire cost"
    )
    hire_rate = models.DecimalField(
        max_digits=15, decimal_places=6, verbose_name="Hire Rate (USD)"
    )

    class Meta:
        abstract = True


class BaseCharterCost(AbsCharterCost):
    """[BASE] 기준 Charter Cost"""

    class Meta:
        verbose_name = "Base Vessel charter hire rate information"
        db_table = "base_vessel_charter_cost"
        unique_together = (("vessel_code", "hire_from_date"),)


class CharterCost(AbsCharterCost, ScenarioBaseModel):
    """[SCE] 시나리오 Charter Cost"""

    class Meta:
        verbose_name = "Vessel charter hire rate information"
        db_table = "sce_vessel_charter_cost"
        unique_together = (("scenario", "vessel_code", "hire_from_date"),)


# 5. Vessel Capacity
class AbsVesselCapacity(models.Model):
    """Vessel Capacity 데이터 필드 (추상)
    선박 용량은 기본적으로 vessel 단위로 관리하나,
    미래에는 lane, vvd 단위로 선박 용량 입력할 수 있으므로 컬럼 유지
    해당 테이블의 vessel_capacity를 모델에서 사용
    """

    trade_code = models.CharField(max_length=10, verbose_name="Trade Code / 3 alpha")
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    vessel_code = models.CharField(
        max_length=10, verbose_name="Vessel Code / 4 alphanum"
    )
    voyage_number = models.CharField(
        max_length=20, verbose_name="Voyage Number / 4 numeric digits"
    )
    direction = models.CharField(
        max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E, S, N}"
    )
    vessel_capacity = models.IntegerField(verbose_name="Vessel Capacity (TEU)")
    reefer_capacity = models.IntegerField(
        verbose_name="Max Reefer Containers (Plug Capacity)"
    )

    class Meta:
        abstract = True


class BaseVesselCapacity(AbsVesselCapacity):
    """[BASE] 기준 Vessel Capacity"""

    class Meta:
        verbose_name = "Base Vessel capacity information"
        db_table = "base_vessel_capacity"
        unique_together = (
            ("trade_code", "lane_code", "vessel_code", "voyage_number", "direction"),
        )


class VesselCapacity(AbsVesselCapacity, ScenarioBaseModel):
    """[SCE] 시나리오 Vessel Capacity"""

    class Meta:
        verbose_name = "Vessel capacity information"
        db_table = "sce_vessel_capacity"
        unique_together = (
            (
                "scenario",
                "trade_code",
                "lane_code",
                "vessel_code",
                "voyage_number",
                "direction",
            ),
        )

    def __str__(self):
        return f"{self.trade_code} - {self.lane_code} - {self.vessel_code} - {self.voyage_number} - {self.direction}"


# ==========================================
# Group 3: Cost & Distance
# ==========================================


# 1. Canal Fee
class AbsCanalFee(models.Model):
    """Canal Fee 데이터 필드 (추상)"""

    vessel_code = models.CharField(
        max_length=10, verbose_name="Vessel Code / 4 alphanum"
    )
    direction = models.CharField(
        max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E}"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code where the canal is located {PAPCA, EGSCA}",
    )
    canal_fee = models.DecimalField(
        max_digits=15, decimal_places=6, verbose_name="Canal Transit Fee (USD)"
    )

    class Meta:
        abstract = True


class BaseCanalFee(AbsCanalFee):
    """[BASE] 기준 Canal Fee"""

    class Meta:
        verbose_name = "Base Canal transit fee information"
        db_table = "base_cost_canal_fee"
        unique_together = (("vessel_code", "direction", "port_code"),)


class CanalFee(AbsCanalFee, ScenarioBaseModel):
    """[SCE] 시나리오 Canal Fee"""

    class Meta:
        verbose_name = "Canal transit fee information"
        db_table = "sce_cost_canal_fee"
        unique_together = (("scenario", "vessel_code", "direction", "port_code"),)

    def __str__(self):
        return f"[{self.scenario.id}] {self.vessel_code} @ {self.port_code}"


# 2. Distance
class AbsDistance(models.Model):
    """Distance 데이터 필드 (추상)"""

    from_port_code = models.CharField(max_length=10, verbose_name="From Port Code")
    to_port_code = models.CharField(max_length=10, verbose_name="To Port Code")
    distance = models.IntegerField(verbose_name="Port-to-Port Distance (NM)")
    eca_distance = models.IntegerField(verbose_name="Port-to-Port ECA Distance (NM)")

    class Meta:
        abstract = True


class BaseDistance(AbsDistance):
    """[BASE] 기준 Distance"""

    class Meta:
        verbose_name = "Base Distance and ECA distance between ports"
        db_table = "base_cost_distance"
        unique_together = (("from_port_code", "to_port_code"),)


class Distance(AbsDistance, ScenarioBaseModel):
    """[SCE] 시나리오 Distance"""

    class Meta:
        verbose_name = "Distance and ECA distance between ports"
        db_table = "sce_cost_distance"
        unique_together = (("scenario", "from_port_code", "to_port_code"),)

    def __str__(self):
        return f"[{self.scenario.id}] {self.from_port_code} -> {self.to_port_code}"


# 4. TS Cost
class AbsTSCost(models.Model):
    """TS Cost 데이터 필드 (추상)"""

    base_year_month = models.CharField(
        max_length=6, verbose_name="Year and month used as the base period / YYYYMM"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    # currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
    ts_cost = models.IntegerField(verbose_name="Transshipment Cost (USD)")

    class Meta:
        abstract = True


class BaseTSCost(AbsTSCost):
    """[BASE] 기준 TS Cost"""

    class Meta:
        verbose_name = "Base Transshipment cost per port"
        db_table = "base_cost_ts_cost"
        unique_together = (("base_year_month", "port_code"),)


class TSCost(AbsTSCost, ScenarioBaseModel):
    """[SCE] 시나리오 TS Cost"""

    class Meta:
        verbose_name = "Transshipment cost per port"
        db_table = "sce_cost_ts_cost"
        unique_together = (("scenario", "base_year_month", "port_code"),)


# ==========================================
# Group 4: Bunker
# ==========================================


# 1. Bunker Consumption Sea
class AbsBunkerConsumptionSea(models.Model):
    """Bunker Consumption Sea 데이터 필드 (추상)"""

    base_year_month = models.CharField(
        max_length=6, verbose_name="Year and month used as the base period / YYYYMM"
    )
    vessel_capacity = models.IntegerField(
        verbose_name="Vessel Capacity (TEU), 1851 types"
    )
    sea_speed = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Speed (Knot), 13 types consisting of 0.5 difference from 14 to 20",
    )
    bunker_consumption = models.DecimalField(
        max_digits=25,
        decimal_places=13,
        verbose_name="Daily bunker consumption at sea (Ton)",
    )

    class Meta:
        abstract = True


class BaseBunkerConsumptionSea(AbsBunkerConsumptionSea):
    """[BASE] 기준 Bunker Consumption Sea"""

    class Meta:
        verbose_name = "Base Daily bunker consumption by vessel size and speed at sea"
        db_table = "base_bunker_consumption_sea"
        unique_together = (("base_year_month", "vessel_capacity", "sea_speed"),)


class BunkerConsumptionSea(AbsBunkerConsumptionSea, ScenarioBaseModel):
    """[SCE] 시나리오 Bunker Consumption Sea"""

    class Meta:
        verbose_name = "Daily bunker consumption by vessel size and speed at sea"
        db_table = "sce_bunker_consumption_sea"
        unique_together = (
            ("scenario", "base_year_month", "vessel_capacity", "sea_speed"),
        )


# 2. Bunker Consumption Port
class AbsBunkerConsumptionPort(models.Model):
    """Bunker Consumption Port 데이터 필드 (추상)"""

    base_year_month = models.CharField(
        max_length=6, verbose_name="Year and month used as the base period / YYYYMM"
    )
    vessel_capacity = models.IntegerField(
        verbose_name="Vessel Capacity (TEU), 1851 types"
    )
    port_stay_bunker_consumption = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Hourly bunker consumption during port stay (Ton)",
    )
    idling_bunker_consumption = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Hourly bunker consumption during idling (Ton)",
    )
    pilot_inout_bunker_consumption = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Hourly bunker consumption during pilot in/out (Ton)",
    )

    class Meta:
        abstract = True


class BaseBunkerConsumptionPort(AbsBunkerConsumptionPort):
    """[BASE] 기준 Bunker Consumption Port"""

    class Meta:
        verbose_name = "Base bunker consumption per hour by vessel size during port stay and idling"
        db_table = "base_bunker_consumption_port"
        unique_together = (("base_year_month", "vessel_capacity"),)


class BunkerConsumptionPort(AbsBunkerConsumptionPort, ScenarioBaseModel):
    """[SCE] 시나리오 Bunker Consumption Port"""

    class Meta:
        verbose_name = (
            "bunker consumption per hour by vessel size during port stay and idling"
        )
        db_table = "sce_bunker_consumption_port"
        unique_together = (("scenario", "base_year_month", "vessel_capacity"),)


# 3. Bunker Price
class AbsBunkerPrice(models.Model):
    """Bunker Price 데이터 필드 (추상)"""

    base_year_month = models.CharField(
        max_length=6, verbose_name="Year and month used as the base period / YYYYMM"
    )
    trade_code = models.CharField(max_length=10, verbose_name="Trade Code / 3 alpha")
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    bunker_type = models.CharField(
        max_length=4,
        choices=BUNKER_TYPE_CHOICES,
        verbose_name="Bunker type {LSFO: Low Sulphur Fuel Oil, MGO: Marine Gas Oil}",
    )
    bunker_price = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="Bunker Price (USD per Ton)"
    )

    class Meta:
        abstract = True


class BaseBunkerPrice(AbsBunkerPrice):
    """[BASE] 기준 Bunker Price"""

    class Meta:
        verbose_name = "Base Bunker price per ton by Lane and Trade and Bunker type"
        db_table = "base_bunker_price"
        unique_together = (
            ("base_year_month", "trade_code", "lane_code", "bunker_type"),
        )


class BunkerPrice(AbsBunkerPrice, ScenarioBaseModel):
    """[SCE] 시나리오 Bunker Price"""

    class Meta:
        verbose_name = "Bunker price per ton by Lane and Trade and Bunker type"
        db_table = "sce_bunker_price"
        unique_together = (
            ("scenario", "base_year_month", "trade_code", "lane_code", "bunker_type"),
        )


# ==========================================
# Group 6: Constraints
# ==========================================
# 1. Fixed Vessel Deployment
class AbsFixedVesselDeployment(models.Model):
    """Fixed Vessel Deployment 데이터 필드 (추상)
    [제약조건 1] Lane별 선박 투입 제약
    특정 Lane에 특정 선박을 '반드시 투입(Include)'하거나 '투입 금지(Exclude)'합니다.
    """

    lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
    vessel_code = models.CharField(
        max_length=20, verbose_name="Vessel Code / 4 alphanum"
    )
    effective_from_date = models.DateTimeField(
        verbose_name="Effective date from which the deployment is applied."
    )
    deployment_type = models.CharField(
        max_length=1,
        choices=DEPLOYMENT_TYPE_CHOICES,
        default="I",
        verbose_name="Indicates whether the vessel must be included in or excluded from the lane {I: Include, E: Exclude}",
    )
    remark = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Remark"
    )

    class Meta:
        abstract = True


class BaseFixedVesselDeployment(AbsFixedVesselDeployment):
    """[BASE] 기준 Fixed Vessel Deployment"""

    class Meta:
        verbose_name = "Base Constraints for fixed vessel deployment on specific lanes"
        db_table = "base_constraint_fixed_deployment"
        unique_together = (("lane_code", "vessel_code", "effective_from_date"),)


class FixedVesselDeployment(AbsFixedVesselDeployment, ScenarioBaseModel):
    """[SCE] 시나리오 Fixed Vessel Deployment"""

    class Meta:
        verbose_name = "Constraints for fixed vessel deployment on specific lanes"
        db_table = "sce_constraint_fixed_deployment"
        unique_together = (
            ("scenario", "lane_code", "vessel_code", "effective_from_date"),
        )

    def __str__(self):
        type_str = self.get_deployment_type_display()
        return (
            f"[{self.scenario.id}] {self.lane_code} - {self.vessel_code} ({type_str})"
        )


# 2. Fixed Vessel Event
class AbsFixedScheduleChange(models.Model):
    """Fixed Schedule Change 데이터 필드 (추상)
    [제약조건 2] 선박별 스케줄 변경 이벤트 (Point in Time)
    특정 시점에 발생하는 Phase In / Phase Out / Omission 등을 관리합니다.
    """

    vessel_code = models.CharField(
        max_length=20, verbose_name="Vessel Code / 4 alphanum"
    )
    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    schedule_change_status_code = models.CharField(
        max_length=1,
        choices=SCHEDULE_CHANGE_STATUS_CODE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Schedule Change Status {A: Ad hoc Call, I: Phase In, L: Vessel Slide, O: Phase Out, S: Port Omission, R: Port Call Swap}",
    )
    eta = models.DateTimeField(verbose_name="Estimated Time of Arrival")
    remark = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Remark"
    )

    class Meta:
        abstract = True


class BaseFixedScheduleChange(AbsFixedScheduleChange):
    """[BASE] 기준 Fixed Schedule Change"""

    class Meta:
        verbose_name = "Base Constraints for fixed schedule change on specific vessels"
        db_table = "base_constraint_fixed_schedule_change"
        unique_together = (
            ("vessel_code", "port_code", "schedule_change_status_code", "eta"),
        )


class FixedScheduleChange(AbsFixedScheduleChange, ScenarioBaseModel):
    """[SCE] 시나리오 Fixed Schedule Change"""

    class Meta:
        verbose_name = "Fixed Constraints for fixed schedule change on specific vessels"
        db_table = "sce_constraint_fixed_schedule_change"
        unique_together = (
            (
                "scenario",
                "vessel_code",
                "port_code",
                "schedule_change_status_code",
                "eta",
            ),
        )

    def __str__(self):
        return (
            f"[{self.scenario.id}] {self.vessel_code} : {self.port_code} "
            f"({self.get_schedule_change_status_code_display()}) @ {self.eta.date()}"
        )


# 3. Port Constraint
class AbsPortConstraint(models.Model):
    """Port Constraint 데이터 필드 (추상)
    [제약조건 3] 항만 입항 제약
    특정 항구(또는 터미널)에 들어갈 수 있는 선박의 크기를 제한합니다.
    """

    port_code = models.CharField(
        max_length=10,
        verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)",
    )
    terminal_code = models.CharField(
        max_length=10,
        default="All",
        verbose_name="Terminal Code (Port Code +2-digit number, e.g., KRPUS01)",
    )
    exclude_vessel_class = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Maximum allowable vessel class size (TEU)",
    )

    class Meta:
        abstract = True


class BasePortConstraint(AbsPortConstraint):
    """[BASE] 기준 Port Constraint"""

    class Meta:
        verbose_name = "Base Constraints on vessel classes prohibited at specific ports"
        db_table = "base_constraint_port"
        unique_together = (("port_code", "terminal_code"),)


class PortConstraint(AbsPortConstraint, ScenarioBaseModel):
    """[SCE] 시나리오 Port Constraint"""

    class Meta:
        verbose_name = "Constraints on vessel classes prohibited at specific ports"
        db_table = "sce_constraint_port"
        unique_together = (("scenario", "port_code", "terminal_code"),)

    def __str__(self):
        return f"[{self.scenario.id}] {self.port_code} - {self.terminal_code} Limit"


class BaseWeekPeriod(models.Model):
    base_year = models.IntegerField(verbose_name="Base Year / YYYY")
    base_week = models.IntegerField(verbose_name="Base Week / WK")
    base_month = models.IntegerField(verbose_name="Base Month / MM")
    week_start_date = models.DateTimeField(verbose_name="Week Start")
    week_end_date = models.DateTimeField(verbose_name="Week End")

    class Meta:
        verbose_name = "Week Period"
        db_table = "base_week_period"
        unique_together = (
            "base_year",
            "base_week",
        )

    def __str__(self):
        return f"{self.base_year}{self.base_week} - {self.week_start_date} - {self.week_end_date}"


####################### 미사용 모델  ##########################
# # 3. Exchange Rate
# class AbsExchangeRate(models.Model):
#     """Exchange Rate 데이터 필드 (추상)"""
#     base_year_month = models.CharField(max_length=6, verbose_name="Year and month used as the base period / YYYYMM")
#     currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
#     exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Exchange Rate")
#
#     class Meta:
#         abstract = True
#
# class BaseExchangeRate(AbsExchangeRate):
#     """[BASE] 기준 Exchange Rate"""
#     class Meta:
#         verbose_name = "Base Exchange Rate"
#         db_table = "base_cost_exchange_rate"
#         unique_together = (("base_year_month", "currency_code"),)
#
# class ExchangeRate(AbsExchangeRate, ScenarioBaseModel):
#     """[SCE] 시나리오 Exchange Rate"""
#     exchange_rate_id = models.AutoField(primary_key=True)
#
#     class Meta:
#         verbose_name = "Exchange Rate"
#         db_table = "sce_cost_exchange_rate"
#         unique_together = (("scenario", "base_year_month", "currency_code"),)
# class OwnVesselCost(BaseModel):
#     own_vessel_cost_id = models.AutoField(primary_key=True)
#     base_year_month = models.CharField(max_length=6, verbose_name="Year and month used as the base period / YYYYMM")
#     slot_price = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Slot Price")
#
#     class Meta:
#         verbose_name = "Own Vessel Cost"
#         db_table = "cas_cost_own_vessel_cost"
#         unique_together = (("scenario", "base_year_month"),)
#
#     def __str__(self):
#         return f"{self.base_year_month}"
# class PortCharge(BaseModel):
#     port_charge_id = models.AutoField(primary_key=True)
#     base_year_month = models.CharField(max_length=6, verbose_name="Year and month used as the base period / YYYYMM")
#     port_code = models.CharField(max_length=10, verbose_name="Port Code / 2-alpha country code + 3-alpha port code, e.g., KRPUS)")
##     currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
#     tonnage_port_yn = models.CharField(max_length=1, choices=YN_CHOICES, verbose_name="Tonnage Port YN")
#     vessel_class_capacity = models.IntegerField(verbose_name="Vessel class capacity (TEU) {4000, 6000, 8000, 10000, 13000, 20000}")

#     port_charge = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Port Charge")
#
#     class Meta:
#         verbose_name = "Port Charge"
#         db_table = "cas_cost_port_charge"
#         unique_together = (("scenario", "base_year_month", "port_code", "tonnage_port_yn", "vessel_class_capacity"),)
#
#     def __str__(self):
#         return f"{self.base_year_month} - {self.port_code}({self.currency_code}) - {self.vessel_class_capacity}"
# class BunkeringPort(BaseModel):
#     bunkering_port_id = models.AutoField(primary_key=True)
#     base_year_month = models.CharField(max_length=6, verbose_name="Year and month used as the base period / YYYYMM")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
#     bunker_type = models.CharField(max_length=4, choices=BUNKER_TYPE_CHOICES, verbose_name="Bunker type (LSFO or MGO)")
#     bunkering_port_code = models.CharField(max_length=10, verbose_name="Bunkering Port Code")
#     bunkering_port_ratio = models.IntegerField(verbose_name="Bunkering Port Ratio")
#
#     class Meta:
#         verbose_name = "Bunkering Port"
#         db_table = "cas_bunker_bunkering_por"
#         unique_together = (("scenario", "base_year_month", "lane_code", "bunker_type", "bunkering_port_code"),)
#
#     def __str__(self):
#         return f"{self.base_year_month} - {self.lane_code} @ {self.bunkering_port_code} ({self.bunker_type})"
# ==========================================
# Group 5: ETS & Fuel EU
# ==========================================
# class ETSTSPort(BaseModel):
#     ets_ts_port_id = models.AutoField(primary_key=True)
#     ets_ts_port_code = models.CharField(max_length=10, verbose_name="ETS TS Port Code")
#     ets_ts_port_name = models.CharField(max_length=50, verbose_name="ETS TS Port Name")
#     ets_ts_port_country_name = models.CharField(max_length=50, verbose_name="ETS TS Port Country Name")
#
#     class Meta:
#         verbose_name = "ETS TS Port"
#         db_table = "cas_ets_ts_port"
#         unique_together = ("scenario", "ets_ts_port_code",)
#
#     def __str__(self):
#         return f"{self.ets_ts_port_code} - {self.ets_ts_port_name}"
#
#
# class ETSCountry(BaseModel):
#     ets_country_id = models.AutoField(primary_key=True)
#     ets_country_code = models.CharField(max_length=2, verbose_name="ETS Country Code")
#     ets_country_name = models.CharField(max_length=50, verbose_name="ETS Country Name")
#
#     class Meta:
#         verbose_name = "ETS Country"
#         db_table = "cas_ets_country"
#         unique_together = ("scenario", "ets_country_code",)
#
#     def __str__(self):
#         return f"{self.ets_country_code} ({self.ets_country_name})"
#
#
# class ETSBunkerConsumption(BaseModel):
#     ets_bunker_consumption_id = models.AutoField(primary_key=True)
#     bunker_type = models.CharField(max_length=4, choices=BUNKER_TYPE_CHOICES, verbose_name="Bunker type (LSFO or MGO)")
#     bunker_consumption = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Bunker Consumption")
#
#     class Meta:
#         verbose_name = "ETS Bunker Consumption"
#         db_table = "cas_ets_bunker_consumption"
#         unique_together = ("scenario", "bunker_type",)
#
#     def __str__(self):
#         return f"{self.bunker_type}"
#
#
# class ETSEUA(BaseModel):
#     """EU Allowance Price/Data"""
#     ets_eua_id = models.AutoField(primary_key=True)
#     trade_code = models.CharField(max_length=10, verbose_name="Trade Code / 3 alpha")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
#     vessel_code = models.CharField(max_length=10, verbose_name="Vessel Code / 4 alphanum")
#     voyage_number = models.CharField(max_length=20, verbose_name="Voyage Number / 4 numeric digits")
#     direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction {W, E, S, N}")
#     base_year_month = models.CharField(max_length=6, verbose_name="Year and month used as the base period / YYYYMM")
#     eu_allowance = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="EU Allowance")
#     euro_exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="EURO Exchange Rate")
#
#     class Meta:
#         verbose_name = "ETS EUA"
#         db_table = "cas_ets_eua"
#         unique_together = (("scenario", "trade_code", "lane_code", "vessel_code", "voyage_number", "direction",
#                             "base_year_month"),)
#
#     def __str__(self):
#         return f"{self.base_year_month} - {self.trade_code} - {self.lane_code} - {self.vessel_code} - {self.voyage_number} - {self.direction}"
#
#
# class FuelEU(BaseModel):
#     fuel_eu_id = models.AutoField(primary_key=True)
#     trade_code = models.CharField(max_length=10, verbose_name="Trade Code / 3 alpha")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code / 3 alphanum")
#     base_year_week = models.CharField(max_length=6, verbose_name="Base Year Week")
#     fuel_energy_content = models.IntegerField(verbose_name="Fuel Energy Content")
#     ghg_penalty_rate = models.IntegerField(verbose_name="GHG Penalty Rate")
#
#     class Meta:
#         verbose_name = "FUEL EU"
#         db_table = "cas_fuel_eu"
#         unique_together = (("scenario", "trade_code", "lane_code"),)
#
#     def __str__(self):
#         return f"{self.trade_code} - {self.lane_code} - {self.base_year_week}"
#
#
# class FuelEUBunker(BaseModel):
#     fuel_eu_bunker_id = models.AutoField(primary_key=True)
#     bunker_type = models.CharField(max_length=4, verbose_name="Bunker type (LSFO or MGO)")
#     ghg_intensity = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="GHG Intensity")
#     lower_calorific_value = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Lower Calorific Value")
#
#     class Meta:
#         verbose_name = "Fuel Eu Bunker"
#         db_table = "cas_fuel_eu_bunker"
#         unique_together = ("scenario", "bunker_type",)
#
#     def __str__(self):
#         return f"{self.bunker_type} (GHG: {self.ghg_intensity})"
#
#
# class GreenhouseGasTarget(BaseModel):
#     greenhouse_gas_target_id = models.AutoField(primary_key=True)
#     ghg_target_effective_from_year = models.CharField(max_length=4, verbose_name="GHG Target Effective From Year")
#     ghg_target_effective_to_year = models.CharField(max_length=4, verbose_name="GHG Target Effective To Year")
#     ghg_target_co2 = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="GHG Target (gCO2e/MJ)")
#
#     class Meta:
#         verbose_name = "Greenhouse Gas Target"
#         db_table = "cas_fuel_eu_ghg_target"
#         unique_together = ("scenario", "ghg_target_effective_from_year",)
#
#     def __str__(self):
#         return f"{self.ghg_target_effective_from_year}~{self.ghg_target_effective_to_year}:{self.ghg_target_co2}"


# ==========================================
# Simulation Analysis & Results
# ==========================================
class SimulationRun(CommonModel):
    """시뮬레이션 실행 기록"""

    scenario = models.ForeignKey(
        ScenarioInfo, on_delete=models.CASCADE, related_name="simulation_runs"
    )
    run_name = models.CharField(
        max_length=100,
        verbose_name="Run Name",
        help_text="Name for this simulation run",
    )
    parameters = models.JSONField(
        default=dict,
        verbose_name="Simulation Parameters",
        help_text="Parameters used for this simulation run",
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Start Time")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="End Time")
    status = models.CharField(
        max_length=20,
        choices=(
            ("RUNNING", "Running"),
            ("COMPLETED", "Completed"),
            ("FAILED", "Failed"),
            ("CANCELLED", "Cancelled"),
        ),
        default="RUNNING",
    )
    results_summary = models.JSONField(
        default=dict,
        verbose_name="Results Summary",
        help_text="Key performance indicators and summary metrics",
    )

    class Meta:
        db_table = "sce_simulation_run"
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.scenario.id} - {self.run_name}"

    @property
    def duration(self):
        """Calculate simulation run duration"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


class ScenarioComparison(CommonModel):
    """시나리오 비교 분석"""

    name = models.CharField(max_length=100, verbose_name="Comparison Name")
    base_scenario = models.ForeignKey(
        ScenarioInfo,
        on_delete=models.CASCADE,
        related_name="base_comparisons",
        verbose_name="Base Scenario",
    )
    compare_scenarios = models.ManyToManyField(
        ScenarioInfo,
        related_name="compare_comparisons",
        verbose_name="Scenarios to Compare",
    )
    comparison_metrics = models.JSONField(
        default=list,
        verbose_name="Comparison Metrics",
        help_text="List of metrics to compare (e.g., cost, utilization, schedule adherence)",
    )
    results = models.JSONField(default=dict, verbose_name="Comparison Results")

    class Meta:
        db_table = "sce_scenario_comparison"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comparison: {self.name}"


class KPISnapshot(CommonModel):
    """시나리오별 KPI 스냅샷"""

    scenario = models.ForeignKey(
        ScenarioInfo, on_delete=models.CASCADE, related_name="kpi_snapshots"
    )
    snapshot_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Snapshot Date"
    )

    # Key Performance Indicators
    total_vessels = models.IntegerField(default=0, verbose_name="Total Vessels")
    total_capacity_teu = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total Capacity (TEU)"
    )
    utilization_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="Utilization Rate (%)"
    )
    total_voyages = models.IntegerField(default=0, verbose_name="Total Voyages")
    average_port_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Average Port Time (Hours)",
    )

    # Cost metrics (can be expanded)
    estimated_fuel_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Estimated Fuel Cost"
    )
    estimated_charter_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Estimated Charter Cost",
    )

    # Custom metrics
    custom_metrics = models.JSONField(
        default=dict,
        verbose_name="Custom Metrics",
        help_text="Additional custom KPIs specific to this scenario",
    )

    class Meta:
        db_table = "sce_kpi_snapshot"
        ordering = ["-snapshot_date"]
        unique_together = ("scenario", "snapshot_date")

    def __str__(self):
        return f"KPI - {self.scenario.id} ({self.snapshot_date.date()})"
