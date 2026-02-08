from django.db import models
from common.models import CommonModel


SCENARIO_STATUS_CODE = (
    ("T", "TEST"),
    ("N", "Not used"),
)


class ScenarioInfo(CommonModel):
    """
    입력 데이터 덩어리(스냅샷)에 대한 기본 정보를 관리하는 마스터 테이블입니다.
    모든 하위 데이터 테이블은 scenario_id를 통해 이 테이블과 연결됩니다.
    """
    # scenario_id를 문자열 PK로 설정 (예: '202501_BASE', 'TEST_SCENARIO_1')
    id = models.CharField(
        max_length=50,
        primary_key=True,
        db_column="scenario_id",  # DB 컬럼명 유지
        verbose_name="Scenario ID"
    )
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="Description")
    base_year_month = models.CharField(max_length=6, null=True, blank=True, verbose_name="Base Year Month")
    status = models.CharField(max_length=50,  choices=SCENARIO_STATUS_CODE, default='T',verbose_name="Scenario Status")

    class Meta:
        verbose_name = "Scenario Info"
        verbose_name_plural = "Scenario Info"
        db_table = "cas_scenario_info"

    def __str__(self):
        return f"[{self.id}] {self.description}"


# ==========================================
# [공통] 추상 모델 (FK to Scenario + Audit)
# ==========================================
class BaseModel(CommonModel):
    """
    모든 하위 데이터 모델이 상속받는 기본 모델입니다.
    ScenarioInfo에 대한 FK(scenario_id)를 포함합니다.
    """
    scenario = models.ForeignKey(
        ScenarioInfo,
        on_delete=models.CASCADE,
        verbose_name="Scenario ID",
        related_name="%(class)s_set"
    )

    class Meta:
        abstract = True


# ==========================================
# [공통] Choices 정의
# ==========================================
OWN_TYPE_CHOICES = (
    ("O", "Own"),
    ("C", "Chartered"),
)

DIRECTION_CHOICES = (
    ("E", "East"),
    ("W", "West"),
    ("S", "South"),
    ("N", "North"),
)

SCHEDULE_CHANGE_STATUS_CODE_CHOICES = (
    ("A", "Ad hoc Call"),
    ("I", "Phase In"),
    ("L", "Vessel Slide"),
    ("O", "Phase Out"),
    ("S", "Port Omisson"),
    ("R", "Port Call Swap"),
)


FULL_EMPTY_CHOICES = (
    ("F", "Full"),
    ("E", "Empty"),
)

CONTAINER_SIZE_TYPE_CHOICES = (
    ("D2", "D2"),
    ("D4", "D4"),
    ("D5", "D5"),
    ("D7", "D7"),
    ("R2", "R2"),
    ("R5", "R5"),
)

BUNKER_TYPE_CHOICES = (
    ("LSFO", "Low Sulphur Fuel Oil"),
    ("MGO", "Marine Gas Oil"),
)

TURN_PORT_INFO_CD = (
    ("Y", "Y"),
    ("N", "N"),
)
TURN_PORT_SYS_CD = (
    ("Y", "Turning Port "),
    ("N", "First Call or Normal Port "),
    ("F", "Final port"),
)


# ==========================================
# Group 1: Schedule
# ==========================================
class ProformaSchedule(BaseModel):
    """Proforma Schedule Data"""
    proforma_schedule_id = models.AutoField(primary_key=True)
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
    proforma_name = models.CharField(max_length=30, verbose_name="Proforma Name")
    effective_date = models.DateTimeField(verbose_name="Effective Date")
    duration = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Duration")
    declared_capacity = models.CharField(max_length=5, verbose_name="Declared Capacity (Class Code)")
    declared_count = models.IntegerField(verbose_name="Declared Count")
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction")
    port_code = models.CharField(max_length=10, verbose_name="Port Code")
    calling_port_indicator_seq = models.CharField(max_length=2, verbose_name="Calling Port Indicator Seq.")
    calling_port_seq = models.IntegerField(verbose_name="Calling Port Seq.")
    turn_port_info_code = models.CharField(max_length=3, choices=TURN_PORT_INFO_CD, verbose_name="Turn Port Info")
    pilot_in_hours = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Pilot In Hours", default=3)
    etb_day_code = models.CharField(max_length=3, verbose_name="ETB Day Code")
    etb_day_time = models.CharField(max_length=4, verbose_name="ETB Day Time")
    etb_day_number = models.IntegerField(verbose_name="ETB Day Number")
    actual_work_hours = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Actual Work Hours(ETD - ETB)",
                                            default=30)
    etd_day_code = models.CharField(max_length=3, verbose_name="ETD Day Code")
    etd_day_time = models.CharField(max_length=4, verbose_name="ETD Day Time")
    etd_day_number = models.IntegerField(verbose_name="ETD Day Number")
    pilot_out_hours = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Pilot Out Hours", default=3)
    link_distance = models.IntegerField(verbose_name="Link Distance", default=0)
    link_eca_distance = models.IntegerField(null=True, verbose_name="Link ECA Distance", default=0)
    link_speed = models.DecimalField(null=True, max_digits=5, decimal_places=3, verbose_name="Link Speed")
    sea_hours = models.DecimalField(null=True, max_digits=5, decimal_places=3, verbose_name="Sea Hours")
    terminal_code = models.CharField(max_length=10, verbose_name="Terminal Code")

    class Meta:
        verbose_name = "Proforma Schedule"
        db_table = "cas_schedule_proforma"
        unique_together = (("scenario", "lane_code", "proforma_name", "direction", "port_code", "calling_port_indicator_seq"),)

    def __str__(self):
        return f"{self.lane_code} - {self.proforma_name} - {self.direction}- {self.port_code}"


class LongRangeSchedule(BaseModel):
    """Long Range Schedule Data"""
    long_range_schedule_id = models.AutoField(primary_key=True)
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
    vessel_code = models.CharField(max_length=10, verbose_name="Vessel Code")
    voyage_number = models.CharField(max_length=20, verbose_name="Voyage Number")
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction")
    start_port_berthing_year_week = models.CharField(max_length=6, verbose_name="Start Port Berthing Year Week")
    proforma_name = models.CharField(max_length=30, verbose_name="Proforma Name")
    port_code = models.CharField(max_length=10, verbose_name="Port Code")
    calling_port_indicator_seq = models.CharField(max_length=2, verbose_name="Calling Port Indicator Seq.")
    calling_port_seq = models.IntegerField(verbose_name="Calling Port Seq.")
    schedule_change_status_code = models.CharField(max_length=1, choices=SCHEDULE_CHANGE_STATUS_CODE_CHOICES,
                                                   null=True, blank=True,
                                                   verbose_name="Schedule Change Status Code")
    eta_initial_arrival = models.DateTimeField(null=True, blank=True, verbose_name="ETA (Initial Arrival)")
    etb_initial_berthing = models.DateTimeField(null=True, blank=True, verbose_name="ETB (Initial Berthing)")
    etd_initial_departure = models.DateTimeField(null=True, blank=True, verbose_name="ETD (Initial Departure)")
    terminal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Terminal Code")

    class Meta:
        verbose_name = "Long Range Schedule"
        db_table = "cas_schedule_long_range"
        unique_together = (("scenario", "lane_code", "vessel_code", "voyage_number", "direction", "port_code",
                            "calling_port_indicator_seq"),)

    def __str__(self):
        return f"{self.lane_code} - {self.vessel_code} - {self.voyage_number} - {self.direction}- {self.port_code}"


# ==========================================
# Group 2: Vessel
# ==========================================
class VesselInfo(BaseModel):
    """Basic Vessel Information"""
    vessel_info_id = models.AutoField(primary_key=True)
    vessel_code = models.CharField(max_length=4, verbose_name="Vessel Code")
    vessel_name = models.CharField(max_length=50, verbose_name="Vessel Name")
    nominal_capacity = models.IntegerField(verbose_name="Nominal Capacity")
    own_yn = models.CharField(max_length=1, choices=OWN_TYPE_CHOICES, verbose_name="Own YN")
    delivery_port_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Delivery Port Code")
    delivery_date = models.DateTimeField(null=True, blank=True, verbose_name="Delivery Date")
    redelivery_port_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Redelivery Port Code")
    redelivery_date = models.DateTimeField(null=True, blank=True, verbose_name="Redelivery Date")
    next_dock_port_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Next Dock Port Code")
    next_dock_in_date = models.DateTimeField(null=True, blank=True, verbose_name="Next Dock In Date")
    next_dock_out_date = models.DateTimeField(null=True, blank=True, verbose_name="Next Dock Out Date")
    built_port_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Built Port Code")
    built_date = models.CharField(max_length=50, null=True, blank=True, verbose_name="Built Date")

    class Meta:
        verbose_name = "Vessel Info"
        db_table = "cas_vessel_info"
        unique_together = ("scenario", "vessel_code",)

    def __str__(self):
        return f"{self.vessel_code} ({self.vessel_name})"


class CharterCost(BaseModel):
    """Charter Hire / Cost"""
    charter_cost_id = models.AutoField(primary_key=True)
    vessel_code = models.CharField(max_length=4, verbose_name="Vessel Code")
    currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
    hire_from_date = models.DateTimeField(verbose_name="Hire From Date")
    hire_to_date = models.DateTimeField(verbose_name="Hire To Date")
    hire_rate = models.IntegerField(verbose_name="Hire Rate")

    class Meta:
        verbose_name = "Charter Cost"
        db_table = "cas_vessel_charter_cost"
        unique_together = (("scenario", "vessel_code", "currency_code", "hire_from_date"),)

    def __str__(self):
        return f"{self.vessel_code} : {self.hire_from_date} ~ {self.hire_to_date} ({self.currency_code})"


class VesselCapacity(BaseModel):
    """Vessel Loading Capacity"""
    vessel_capacity_id = models.AutoField(primary_key=True)
    trade_code = models.CharField(max_length=10, verbose_name="Trade Code")
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
    vessel_code = models.CharField(max_length=10, verbose_name="Vessel Code")
    voyage_number = models.CharField(max_length=20, verbose_name="Voyage Number")
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction")
    effective_from_date = models.DateTimeField(null=True, blank=True, verbose_name="Effective From Date")
    teu_capacity = models.IntegerField(verbose_name="TEU Capacity")
    reefer_capacity = models.IntegerField(verbose_name="Reefer Capacity")

    class Meta:
        verbose_name = "Vessel Capacity"
        db_table = "cas_vessel_capacity"
        unique_together = (("scenario", "trade_code", "lane_code", "vessel_code", "voyage_number", "direction",
                            "effective_from_date"),)

    def __str__(self):
        return (f"{self.trade_code} - {self.lane_code} - {self.vessel_code}"
                f"{self.voyage_number} - {self.direction} - {self.effective_from_date} ")


# ==========================================
# Group 3: Cost
# ==========================================
class CanalFee(BaseModel):
    canal_fee_id = models.AutoField(primary_key=True)
    vessel_code = models.CharField(max_length=10, verbose_name="Vessel Code")
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction")
    port_code = models.CharField(max_length=10, verbose_name="Port Code")
    canal_fee = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Canal Fee")

    class Meta:
        verbose_name = "Canal Fee"
        db_table = "cas_cost_canal_fee"
        unique_together = (("scenario", "vessel_code", "direction", "port_code"),)

    def __str__(self):
        return f"{self.vessel_code} @ {self.port_code} - {self.direction}"


class Distance(BaseModel):
    distance_id = models.AutoField(primary_key=True)
    from_port_code = models.CharField(max_length=10, verbose_name="From Port Code")
    to_port_code = models.CharField(max_length=10, verbose_name="To Port Code")
    distance = models.IntegerField(verbose_name="Distance")
    eca_distance = models.IntegerField(verbose_name="ECA Distance")

    class Meta:
        verbose_name = "Distance"
        db_table = "cas_cost_distance"
        unique_together = (("scenario", "from_port_code", "to_port_code"),)

    def __str__(self):
        return f"{self.from_port_code} -> {self.to_port_code}"


class ExchangeRate(BaseModel):
    exchange_rate_id = models.AutoField(primary_key=True)
    base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
    currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Exchange Rate")

    class Meta:
        verbose_name = "Exchange Rate"
        db_table = "cas_cost_exchange_rate"
        unique_together = (("scenario", "base_year_month", "currency_code"),)

    def __str__(self):
        return f"{self.base_year_month} - {self.currency_code}"


# class OwnVesselCost(BaseModel):
#     own_vessel_cost_id = models.AutoField(primary_key=True)
#     base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
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
#     base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
#     port_code = models.CharField(max_length=10, verbose_name="Port Code")
#     currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
#     tonnage_port_yn = models.CharField(max_length=1, choices=YN_CHOICES, verbose_name="Tonnage Port YN")
#     nominal_capacity = models.IntegerField(verbose_name="Nominal Capacity")
#     port_charge = models.DecimalField(max_digits=15, decimal_places=6, verbose_name="Port Charge")
#
#     class Meta:
#         verbose_name = "Port Charge"
#         db_table = "cas_cost_port_charge"
#         unique_together = (("scenario", "base_year_month", "port_code", "currency_code", "tonnage_port_yn", "nominal_capacity"),)
#
#     def __str__(self):
#         return f"{self.base_year_month} - {self.port_code}({self.currency_code}) - {self.nominal_capacity}"


class TSCost(BaseModel):
    """Transshipment Cost"""
    ts_cost_id = models.AutoField(primary_key=True)
    base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
    port_code = models.CharField(max_length=10, verbose_name="Port Code")
    full_empty_code = models.CharField(max_length=1, choices=FULL_EMPTY_CHOICES, verbose_name="Full Empty Code")
    container_code = models.CharField(max_length=4, choices=CONTAINER_SIZE_TYPE_CHOICES, verbose_name="Container Code")
    currency_code = models.CharField(max_length=3, verbose_name="Currency Code")
    ts_cost = models.IntegerField(verbose_name="TS Cost")

    class Meta:
        verbose_name = "TS Cost"
        db_table = "cas_cost_ts_cost"
        unique_together = (("scenario", "base_year_month", "port_code", "full_empty_code", "container_code", "currency_code"),)

    def __str__(self):
        return (f"{self.base_year_month} - {self.port_code} ({self.currency_code}) - {self.full_empty_code} "
                f"- {self.container_code}")


# ==========================================
# Group 4: Bunker
# ==========================================
class BunkerConsumptionSea(BaseModel):
    bunker_consumption_sea_id = models.AutoField(primary_key=True)
    base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
    nominal_capacity = models.IntegerField(verbose_name="Nominal Capacity")
    sea_speed = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Sea Speed")
    bunker_consumption = models.DecimalField(max_digits=25, decimal_places=13, verbose_name="Bunker Consumption")

    class Meta:
        verbose_name = "Bunker Consumption Sea"
        db_table = "cas_bunker_consumption_sea"
        unique_together = (("scenario", "base_year_month", "nominal_capacity", "sea_speed"),)

    def __str__(self):
        return f"{self.base_year_month} - {self.nominal_capacity}TEU - {self.sea_speed}kts"


class BunkerConsumptionPort(BaseModel):
    bunker_consumption_port_id = models.AutoField(primary_key=True)
    base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
    nominal_capacity = models.IntegerField(verbose_name="Nominal Capacity")
    port_stay_bunker_consumption = models.DecimalField(max_digits=5, decimal_places=3,
                                                       verbose_name="Port Stay Bunker Consumption")
    idling_bunker_consumption = models.DecimalField(max_digits=5, decimal_places=3,
                                                    verbose_name="Idling Bunker Consumption")
    pilot_inout_bunker_consumption = models.DecimalField(max_digits=5, decimal_places=3,
                                                         verbose_name="Pilot In/Out Bunker Consumption")

    class Meta:
        verbose_name = "Bunker Consumption Port"
        db_table = "cas_bunker_consumption_port"
        unique_together = (("scenario", "base_year_month", "nominal_capacity"),)

    def __str__(self):
        return f"{self.base_year_month} - {self.nominal_capacity}TEU (Port)"


# class BunkeringPort(BaseModel):
#     bunkering_port_id = models.AutoField(primary_key=True)
#     base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
#     bunker_type = models.CharField(max_length=4, choices=BUNKER_TYPE_CHOICES, verbose_name="Bunker Type")
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


class BunkerPrice(BaseModel):
    bunker_price_id = models.AutoField(primary_key=True)
    base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
    trade_code = models.CharField(max_length=10, verbose_name="Trade Code")
    lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
    bunker_type = models.CharField(max_length=4, choices=BUNKER_TYPE_CHOICES, verbose_name="Bunker Type")
    bunker_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Bunker Price")

    class Meta:
        verbose_name = "Bunker Price"
        db_table = "cas_bunker_bunker_price"
        unique_together = (("scenario", "base_year_month", "trade_code", "lane_code", "bunker_type"),)

    def __str__(self):
        return f"{self.base_year_month} - {self.trade_code} - {self.lane_code}({self.bunker_type})"


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
#     bunker_type = models.CharField(max_length=4, choices=BUNKER_TYPE_CHOICES, verbose_name="Bunker Type")
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
#     trade_code = models.CharField(max_length=10, verbose_name="Trade Code")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
#     vessel_code = models.CharField(max_length=10, verbose_name="Vessel Code")
#     voyage_number = models.CharField(max_length=20, verbose_name="Voyage Number")
#     direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, verbose_name="Direction")
#     base_year_month = models.CharField(max_length=6, verbose_name="Base Year Month")
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
#     trade_code = models.CharField(max_length=10, verbose_name="Trade Code")
#     lane_code = models.CharField(max_length=10, verbose_name="Lane Code")
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
#     bunker_type = models.CharField(max_length=4, verbose_name="Bunker Type")
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


class master_week_period(BaseModel):
    master_week_period_id = models.AutoField(primary_key=True)
    base_year = models.IntegerField(verbose_name="Base Year")
    base_week = models.IntegerField(verbose_name="Base Week")
    base_month = models.IntegerField(verbose_name="Base Month")
    week_start_date = models.DateTimeField(verbose_name="Week Start")
    week_end_date = models.DateTimeField(verbose_name="Week End")

    class Meta:
        verbose_name = "Week Period"
        db_table = "cas_week_period"
        unique_together = ("scenario", "base_week",)

    def __str__(self):
        return f"{self.base_week} - {self.week_start} - {self.week_end}"