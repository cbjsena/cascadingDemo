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
# Simulation Engine Choices
# ==========================================
SIMULATION_SOLVER_CHOICES = {
    "EXACT": [
        {"value": "cplex", "label": "IBM ILOG CPLEX"},
        {"value": "gurobi", "label": "Gurobi Optimizer"},
        {"value": "xpress", "label": "FICO Xpress"},
        {"value": "ortools", "label": "Google OR-Tools"},
    ],
    "EFFICIENT": [
        {"value": "meta_default", "label": "Metaheuristic Engine"},
        {"value": "meta_fast", "label": "Metaheuristic (Fast Track)"},
    ],
    "FAST": [
        {"value": "greedy_rules", "label": "Rule-based Greedy Engine"},
        {"value": "greedy_fast", "label": "Greedy (Fast Results)"},
    ],
}

# ==========================================
# Excel Manager
# ==========================================
# Template 기본값
EXCEL_DEFAULT_GRID_START_ROW = 6
EXCEL_DEFAULT_DATA_START_ROW = 7
EXCEL_DEFAULT_MERGE_WIDTH = 3
EXCEL_TEMPLATE_EMPTY_ROWS = 10

# 파싱 설정
EXCEL_MAX_SCAN_ROWS = 100
EXCEL_CONSECUTIVE_EMPTY_LIMIT = 3
EXCEL_KEY_COLUMN_INDEX = 2  # 데이터 유무 판별 컬럼 (Port Code)
EXCEL_NO_COLUMN_INDEX = 1

# 라벨 / 섹션명
EXCEL_LABEL_SUMMARY = "Summary"
EXCEL_SECTION_BASIC = "Basic Information"
EXCEL_SECTION_GRID = "Port Schedule"
EXCEL_DEFAULT_TIME = "0000"

# ==========================================
# Bunker Sea Speed Defaults
# ==========================================
# Sea Speed 범위 (Knot) — 0.5 단위
SEA_SPEED_MIN = 14.0
SEA_SPEED_MAX = 20.0
SEA_SPEED_STEP = 0.5

# ==========================================
# Continent Codes (Trade From/To)
# ==========================================
CONTINENT_CODES = [
    ("A", "Asia"),
    ("E", "Europe"),
    ("F", "Africa"),
    ("M", "America"),
    ("-", "Common"),
]
VESSEL_SERVICE_TYPE_CODES = [
    ("I", "Independent Operation"),
    ("J", "Joint Operation"),
    ("O", "CCA Feeder"),
    ("S", "Space Charter"),
]
