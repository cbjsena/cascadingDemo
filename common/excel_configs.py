LABEL_SUMMARY = "Summary"
SECTION_BASIC = "Basic Information"

# --- Proforma Configuration Group ---
PROFORMA_CONFIG = {
    'sheet_title': "Proforma Schedule",

    # Basic Info Header: (좌표, 헤더명, 파싱키)
    'basic_headers': [
        ('A2', 'Snapshot ID', 'data_id', 2),
        ('C2', 'Service Lane Code', 'lane_code', 2),
        ('E2', 'Proforma Name', 'proforma_name', 2),
        ('G2', 'Effective Date', 'effective_date', 2),
        ('I2', 'Declared Capacity', 'capacity', 2),
        ('K2', 'Declared Count', 'count', 2),
        ('M2', 'Duration', 'duration', 2),
    ],

    # [신규] Basic Information 예시 값
    'basic_examples': {
        'data_id': 'default_id',
        'lane_code': 'FP1',
        'proforma_name': '7001',
        'effective_date': '2026-07-01',
        'capacity': '20000',
        'count': '19',
        'duration': '42.0'
    },

    # Grid Headers: (헤더명, 파싱키, 컬럼인덱스)
    'grid_headers': [
        ("No.", "no", 1),
        ("Port\nCode", "port_code", 2),
        ("Direction", "direction", 3),
        ("Turning\nPort", "turn_info", 4),
        ("Pilot\nIn", "pilot_in", 5),
        ("ETB\nNo.", "etb_no", 6),
        ("ETB\nDay", "etb_day", 7),
        ("ETB\nTime", "etb_time", 8),
        ("Work\nHours", "work_hours", 9),
        ("ETD\nNo.", "etd_no", 10),
        ("ETD\nDay", "etd_day", 11),
        ("ETD\nTime", "etd_time", 12),
        ("Pilot\nOut", "pilot_out", 13),
        ("Dist.", "dist", 14),
        ("ECA\nDist.", "eca_dist", 15),
        ("Spd.", "spd", 16),
        ("Sea\nTime", "sea_time", 17),
        ("Terminal\nCode", "terminal", 18),
    ],

    # Grid 첫 번째 행 예시 값
    'grid_examples': {
        'no': 1,
        'port_code': 'KRPUS',
        'direction': 'E',
        'turn_info': 'N',
        'pilot_in': 2,
        'etb_no': 0, 'etb_day': 'MON', 'etb_time': '0800',
        'work_hours': 24,
        'etd_no': 1, 'etd_day': 'TUE', 'etd_time': '0800',
        'pilot_out': 2.5,
        'dist': 0, 'eca_dist': 0, 'spd': 0, 'sea_time': 0,
        'terminal': 'KRPUS01'
    },

    # Summary Columns: {Column Index: Column Letter}
    # 'summary_cols': {
    #     5: 'E', 9: 'I', 13: 'M', 14: 'N', 17: 'Q'
    # },

    'col_widths': [5, 12, 10, 10, 8, 8, 8, 8, 10, 8, 8, 8, 10, 8, 8, 8, 10, 15],

    # 추가적인 옵션들 (시작 행 등)
    'start_row_grid': 6,
    'start_row_data': 7,
}