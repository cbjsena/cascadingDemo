from django.db import models

from common.models import CommonModel

SCENARIO_STATUS_CODE = (("T", "TEST"), ("N", "Not used"))
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
    id = models.CharField(
        max_length=50,
        primary_key=True,
        db_column="scenario_id",
        verbose_name="Scenario ID",
    )
    description = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Description"
    )
    base_year_month = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        verbose_name="Year and month used as the base period / YYYYMM",
    )
    status = models.CharField(
        max_length=50,
        choices=SCENARIO_STATUS_CODE,
        default="T",
        verbose_name="Scenario Status {T: TEST, N: Not used}",
    )

    class Meta:
        verbose_name = "Scenario Info"
        db_table = "sce_scenario_info"  # [변경] cas -> sce

    def __str__(self):
        return f"[{self.id}] {self.description}"


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
        verbose_name="Effective date from which the proforma is applied. "
        "The proforma currently in use is set with a date six months prior."
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
        "The proforma currently in use is set with a date six months prior."
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

    class Meta:
        db_table = "sce_schedule_proforma"
        unique_together = ("scenario", "lane_code", "proforma_name")

    def __str__(self):
        return f"[{self.scenario_id}] {self.lane_code} - {self.proforma_name}"


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

    cascading_seq = models.IntegerField(verbose_name="Sequence")
    own_vessels = models.IntegerField(verbose_name="Own Vessels Count")
    initial_etb_date = models.DateField(
        verbose_name="Initial ETB of the first vessel at the first port"
    )
    effective_start_date = models.DateField(
        verbose_name="Effective start date of the cascading schedule"
    )
    effective_end_date = models.DateField(
        verbose_name="Effective end date of the cascading schedule",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "sce_schedule_cascading"
        # Proforma ID + Seq 조합은 유일해야 함
        unique_together = ("proforma", "cascading_seq")

    def __str__(self):
        return f"[{self.scenario_id}] {self.proforma.proforma_name} - Seq {self.cascading_seq}"


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

    long_range_schedule_id = models.AutoField(primary_key=True)

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

    vessel_info_id = models.AutoField(primary_key=True)

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

    charter_cost_id = models.AutoField(primary_key=True)

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

    vessel_capacity_id = models.AutoField(primary_key=True)

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

    canal_fee_id = models.AutoField(primary_key=True)

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

    distance_id = models.AutoField(primary_key=True)

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

    ts_cost_id = models.AutoField(primary_key=True)

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

    bunker_consumption_sea_id = models.AutoField(primary_key=True)

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

    bunker_consumption_port_id = models.AutoField(primary_key=True)

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

    bunker_price_id = models.AutoField(primary_key=True)

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

    fixed_deployment_id = models.AutoField(primary_key=True)

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

    fixed_schedule_change_id = models.AutoField(primary_key=True)

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
            f"({self.get_event_type_display()}) @ {self.eta.date()}"
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

    constraint_id = models.AutoField(primary_key=True)

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
