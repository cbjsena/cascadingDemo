# common/csv_configs.py

# --- Proforma DB Upload CSV Config ---
# List of Tuples: (CSV Header Name, Data Key)
# Data Key는 Service에서 계산된 Context 딕셔너리의 키와 일치해야 합니다.

PROFORMA_DB_MAP = [
    ("lane_code", "lane_code"),
    ("proforma_name", "proforma_name"),
    ("effective_from_date", "effective_from_date"),
    ("duration", "duration"),
    ("declared_capacity", "capacity"),
    ("declared_count", "count"),
    ("direction", "direction"),
    ("port_code", "port_code"),
    ("calling_port_indicator", "clg_seq"),  # Logic 계산 필드 (Sequence)
    ("calling_port_seq", "port_seq"),
    ("turn_port_info_code", "turn_port_info_code"),
    ("pilot_in_hours", "pilot_in"),
    ("etb_day_number", "etb_no"),
    ("etb_day_code", "etb_day"),
    ("etb_day_time", "etb_time"),
    ("actual_work_hours", "work_hours"),
    ("etd_day_number", "etd_no"),
    ("etd_day_code", "etd_day"),
    ("etd_day_time", "etd_time"),
    ("pilot_out_hours", "pilot_out"),
    ("link_distance", "dist"),
    ("link_eca_distance", "eca_dist"),
    ("link_speed", "spd"),
    ("sea_time_hours", "sea_time"),
    ("terminal_code", "terminal"),
]
