# common/messages.py

# ==========================================
# 성공 메세지 (Success)
# ==========================================
SNAPSHOT_CREATE_SUCCESS = "Snapshot '{data_id}' has been created successfully."
SNAPSHOT_CLONE_SUCCESS = "Snapshot '{data_id}' created (Cloned from '{source_id}')."
SNAPSHOT_DELETE_SUCCESS = "Snapshot '{data_id}' has been deleted successfully."
SCHEDULE_CALCULATED = "Schedule calculated."
SCHEDULE_SAVE_SUCCESS = "Schedule saved successfully."
SCHEDULE_NEW_STARTED = "New schedule started."

# ==========================================
# 에러 메세지 (Error)
# ==========================================
SNAPSHOT_ID_DUPLICATE = "Data ID '{data_id}' already exists."
SNAPSHOT_DELETE_ERROR = "Error deleting snapshot: {error}"
SNAPSHOT_CLONE_ERROR = "Failed to clone data: {error}"
SNAPSHOT_NOT_FOUND = "Snapshot '{data_id}' not found."
PERMISSION_DENIED = "You do not have permission to perform this action."
SAVE_ERROR = "Failed to save: {error}"

# ==========================================
# 경고/정보 (Warning/Info)
# ==========================================
LOGIN_REQUIRED = "Please login to access this page."
FUNC_NOT_IMPLEMENTED = "{func_name} function not implemented yet."


# ==========================================
# 파일 관련 메세지
# ==========================================
UPLOAD_SUCCESS = "Excel file uploaded and parsed successfully."
UPLOAD_FAIL = "Failed to upload excel: {error}"
UPLOAD_FILE_REQUIRED = "Please select a file to upload."
TEMPLATE_MISMATCH = "The uploaded file format does not match the template."
INVALID_EXCEL_FILE = "Invalid Excel file: {error}"