# common/csv_configs.py

# --- Proforma DB Upload CSV Config ---
# List of Tuples: (CSV Header Name, Data Key)
# Data Key는 Service에서 계산된 Context 딕셔너리의 키와 일치해야 합니다.

PROFORMA_DB_MAP = [
    ("data_id", "data_id"),
    ("VSL_SVCE_LANE_CD", "lane_code"),
    ("PF_SVCE_NR", "proforma_name"),
    ("EFFCT_DATE", "effective_date"),
    ("SVCE_LANE_STD_YN", "is_standard"),        # Logic 계산 필드
    ("SVCE_DUR_DAYS", "duration"),
    ("FRST_VSL_CLS_CD", "capacity"),
    ("FRST_VSL_CLS_CT", "count"),
    ("SCH_DIR_CD", "direction"),
    ("PORT_CD", "port_code"),
    ("CLG_PORT_INDC_SEQ", "clg_seq"),           # Logic 계산 필드 (Sequence)
    ("PORT_ROT_SEQ", "no"),
    ("TURN_PORT_PAR_CD", "turn_info"),
    ("TURN_PORT_SYS_CD", "turn_sys"),           # Logic 계산 필드 (Y/N/F)
    ("MANU_IN_HRS", "pilot_in"),
    ("ETB_DAY_CD", "etb_day"),
    ("ETB_TIME_HM", "etb_time"),
    ("ETB_DAY_NR", "etb_no"),
    ("ETD_DAY_CD", "etd_day"),
    ("ETD_TIME_HM", "etd_time"),
    ("ETD_DAY_NR", "etd_no"),
    ("ACTL_WORK_HRS", "work_hours"),
    ("MANU_OUT_HRS", "pilot_out"),
    ("LINK_DIST", "dist"),
    ("LINK_SPD", "spd"),
    ("TRAN_TIME_HRS", "sea_time"),
    ("TML_CD", "terminal")
]