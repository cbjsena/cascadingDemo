# common/constants.py

# ==========================================
# Proforma Schedule Defaults
# ==========================================
# 요일 리스트
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

DEFAULT_DIRECTION = "E"
DEFAULT_TURN_INO = "N"
DEFAULT_TIME = "1200"
DEFAULT_ETB_DAY = DAYS[0]  # 기본 ETB 요일: 일요일
DEFAULT_ETD_DAY = DAYS[1]  # 기본 ETB 요일: 일요일
DEFAULT_PILOT_IN = 2.0
DEFAULT_PILOT_OUT = 2.0
DEFAULT_WORK_HOURS = 24.0
DEFAULT_SEA_TIME = 24.0  # 행 추가 시 ETD -> 다음 ETB 간격 (가정)
DEFAULT_STAY_HOURS = 24.0  # 행 추가 시 ETB -> ETD 간격

DEFAULT_BASE_YEAR_WEEK = "202605"

# ==========================================
# Bunker Sea Speed Defaults
# ==========================================
# Sea Speed 범위 (Knot) — 0.5 단위
SEA_SPEED_MIN = 14.0
SEA_SPEED_MAX = 20.0
SEA_SPEED_STEP = 0.5
