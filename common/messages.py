# common/messages.py
"""
애플리케이션 전역 메시지 상수 관리 모듈

Django 표준:
- 단일 언어 프로젝트: 문자열 상수 직접 사용 (현재 방식)
- 다국어 지원 필요 시: gettext_lazy 사용으로 전환
  예) from django.utils.translation import gettext_lazy as _
      PERMISSION_DENIED = _("You do not have permission to perform this action.")

사용 예시:
    from common import messages as msg
    messages.error(request, msg.PERMISSION_DENIED)
    messages.success(request, msg.SCENARIO_CREATE_SUCCESS.format(scenario_id="SCE001"))
"""

# ==========================================
# 1. 공통 및 인증 (General & Auth)
# ==========================================
PERMISSION_DENIED = "You do not have permission to perform this action."
LOGIN_REQUIRED = "Please login to access this page."
FUNC_NOT_IMPLEMENTED = "{func_name} function not implemented yet."
SAVE_ERROR = "Failed to save: {error}"
LOAD_ERROR = "Failed to load: {error}"  # Fixed: was "Failed to save"
DATA_NOT_FOUND = "Data not found."
MISSING_REQUIRED_FIELDS = "Missing required fields."
MISSING_REQUIRED_FIELDS_FOR = "Missing required fields for {target}."

# ==========================================
# 2. 시나리오 관리 (Scenario)
# ==========================================
# Success
SCENARIO_CREATE_SUCCESS = "Scenario '{scenario_id}' has been created successfully."
SCENARIO_CLONE_SUCCESS = "Scenario '{scenario_id}' created (Cloned from '{source_id}')."
SCENARIO_DELETE_SUCCESS = "Scenario '{scenario_id}' has been deleted successfully."

# Error
SCENARIO_ID_DUPLICATE = "Scenario ID '{scenario_id}' already exists."
SCENARIO_NOT_FOUND = "Scenario '{scenario_id}' not found."
SCENARIO_DELETE_ERROR = "Error deleting scenario: {error}"
SCENARIO_CLONE_ERROR = "Failed to clone data: {error}"

# ==========================================
# 3. 스케줄 관리 (Schedule)
# ==========================================
SCHEDULE_NEW_STARTED = "New schedule started."
SCHEDULE_CALCULATED = "Schedule calculated."
SCHEDULE_SAVE_SUCCESS = "Schedule saved successfully."
SCHEDULE_LOAD_ERROR = "Failed to load schedule: {error}"
INVALID_PARAMETERS = "Invalid parameters."

# ==========================================
# 3-1. Cascading Schedule
# ==========================================
CASCADING_SAVE_SUCCESS = "Cascading Schedule saved successfully."
CASCADING_LRS_CREATE_SUCCESS = "Cascading & Long Range Schedule created successfully."
CASCADING_NOT_FOUND = "Cascading Schedule not found."
CASCADING_PROCESS_ERROR = "Failed to process: {error}"

# ==========================================
# 3-2. Proforma Schedule
# ==========================================
PROFORMA_NOT_FOUND = "Proforma Schedule not found."
PROFORMA_MASTER_NOT_FOUND = "Proforma Schedule (Master) not found."
PROFORMA_DETAIL_NOT_FOUND = "Proforma Schedule Details not found."
PROFORMA_INVALID_DURATION = "Invalid Proforma Duration (0 or None)."

# ==========================================
# 4. 엑셀, csv 업로드 (Web UI)
# ==========================================
UPLOAD_FILE_REQUIRED = "Please select a file to upload."
UPLOAD_SUCCESS = "Excel file uploaded and parsed successfully."
UPLOAD_FAIL = "Failed to upload excel: {error}"
TEMPLATE_MISMATCH = "The uploaded file format does not match the template."
INVALID_EXCEL_FILE = "Invalid Excel file: {error}"
INVALID_DATA_FORMAT = "Column '{column}' expects {internal_type}, but got '{value}'"
INVALID_DATE_FORMAT = "Column '{column}' expects Date/Time, but got '{value}'."
CSV_IMPORT_NOT_CONFIGURED = "CSV import is not configured for this data."
CSV_EXPORT_NOT_CONFIGURED = "CSV export is not configured for this data."
FILE_NOT_SELECTED = "Please select a file to upload."
INVALID_FILE_EXT = "Please upload a valid .{ext} file."
SCENARIO_NOT_SELECTED = "Please select a scenario before proceeding."
CSV_FILE_EMPTY = "The uploaded CSV file is empty."
CSV_IMPORT_RESULT = (
    "{created} {label}(s) imported successfully. {skipped} row(s) skipped."
)


# ==========================================
# 5. 데이터 초기화 및 로그 (CLI / Data Init)
# ==========================================
# 포맷: [TAG] Message
DIR_NOT_FOUND = "Directory not found: {path}"
FILE_NOT_FOUND = "[SKIP] {table}: File not found ({file})"
START_LOADING = "[START] Loading {table}..."
DONE_LOADING = "[DONE] {table}: {count} rows loaded."
EMPTY_CSV = "[EMPTY] {table}: CSV has no data."
LOAD_FAIL = "[FAIL] {table}: {error}"
ROW_ERROR = "[WARN] Row skipped in {table}: {error}"

# ==========================================
# 6. DB 관리 (Database Management)
# ==========================================
DB_COMMENT_UPDATE_START = "Updating database comments (Vendor: {vendor})..."
DB_COMMENT_NOT_SUPPORTED = (
    "Database vendor '{vendor}' does not support comments via this script."
)
DB_TABLE_COMMENT_SUCCESS = "[TABLE] {table}: {comment}"
DB_COLUMN_COMMENT_SUCCESS = "  - [COL] {column}: {comment}"
DB_COMMENT_FAIL = "[FAIL] {target}: {error}"
DB_COMMENT_COMPLETE = "Database comments update completed."

# ==========================================
# 7. 문서 자동 생성 (Doc Generation)
# ==========================================
DOC_GEN_START = "Generating table definition document (PostgreSQL only)..."
DOC_GEN_SKIP = "Skipping document generation (Not PostgreSQL)."
DOC_GEN_SUCCESS = "Table definition saved to '{path}'."
DOC_GEN_FAIL = "Failed to generate table definition: {error}"

# ------------------------------------------------------------------------------
# Auto Setup Messages (Console Output)
# ------------------------------------------------------------------------------
AUTO_SETUP_SUPERUSER_START = "\n[Auto-Setup] Creating default superuser '{username}'..."
AUTO_SETUP_SUPERUSER_SUCCESS = (
    "[Auto-Setup] Superuser '{username}' created successfully."
)
AUTO_SETUP_SUPERUSER_EXIST = (
    "[Auto-Setup] Superuser '{username}' already exists. Skipping."
)
AUTO_SETUP_SUPERUSER_FAILED = "[Auto-Setup] Failed to create superuser: {error}"

AUTO_SETUP_COMMAND_START = "\n[Auto-Setup] Running management command '{command}'..."
AUTO_SETUP_COMMAND_SUCCESS = "[Auto-Setup] Command '{command}' completed successfully."
AUTO_SETUP_COMMAND_FAILED = "[Auto-Setup] Failed to run command '{command}': {error}"
