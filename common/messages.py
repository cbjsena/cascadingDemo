# common/messages.py

# ==========================================
# 1. 공통 및 인증 (General & Auth)
# ==========================================
PERMISSION_DENIED = "You do not have permission to perform this action."
LOGIN_REQUIRED = "Please login to access this page."
FUNC_NOT_IMPLEMENTED = "{func_name} function not implemented yet."
SAVE_ERROR = "Failed to save: {error}"
LOAD_ERROR = "Failed to save: {error}"
DATA_NOT_FOUND = "Data not found."

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

# ==========================================
# 4. 엑셀 업로드 (Web UI)
# ==========================================
UPLOAD_FILE_REQUIRED = "Please select a file to upload."
UPLOAD_SUCCESS = "Excel file uploaded and parsed successfully."
UPLOAD_FAIL = "Failed to upload excel: {error}"
TEMPLATE_MISMATCH = "The uploaded file format does not match the template."
INVALID_EXCEL_FILE = "Invalid Excel file: {error}"

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
