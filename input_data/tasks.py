"""
시나리오 Export Celery Task
- 대량 데이터 Export 시 브라우저 타임아웃(504) 방지
- 백그라운드에서 JSON 생성 + ZIP 압축 수행
- 완료 후 상태/다운로드 경로를 결과로 반환
"""

import logging
import os
import time

from django.conf import settings

from celery import shared_task

from input_data.services.export_configs import (
    EXPORT_BASE_DIR,
    EXPORT_FILE_EXPIRE_SECONDS,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="input_data.export_scenario",
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def export_scenario_task(self, scenario_id):
    """
    시나리오 전체 데이터를 JSON + ZIP으로 Export.

    Args:
        scenario_id: 대상 시나리오 ID

    Returns:
        {
            'status': 'SUCCESS',
            'scenario_id': 42,
            'scenario_code': 'SCE-042',
            'total_records': 128,
            'files': {'_meta.json': 1, ...},
            'zip_download_url': '/media/exports/scenarios/scenario_42_data.zip',
        }
    """
    from input_data.services.scenario_export_service import ScenarioExportService

    # Celery 진행 상태 콜백
    def progress_callback(pct, step):
        self.update_state(
            state="PROGRESS",
            meta={
                "scenario_id": scenario_id,
                "step": step,
                "progress": pct,
            },
        )

    progress_callback(0, "초기화 중...")

    try:
        service = ScenarioExportService(scenario_id)
        result = service.export_all(progress_callback=progress_callback)

        # ZIP 파일의 상대 URL 생성
        zip_relative = os.path.relpath(result["zip_path"], settings.MEDIA_ROOT)
        zip_download_url = f"{settings.MEDIA_URL}{zip_relative}"

        # JSON 폴더 정리 (ZIP만 남김)
        if os.path.exists(service.output_dir):
            import shutil

            shutil.rmtree(service.output_dir)

        logger.info(
            "Export task 완료: scenario_id=%d, records=%d",
            scenario_id,
            result["total_records"],
        )

        return {
            "status": "SUCCESS",
            "scenario_id": scenario_id,
            "scenario_code": result["meta"]["code"],
            "total_records": result["total_records"],
            "files": result["files"],
            "zip_download_url": zip_download_url,
        }

    except Exception:
        logger.exception("Export task 실패: scenario_id=%d", scenario_id)
        # Celery가 FAILURE로 전환
        raise


@shared_task(name="input_data.cleanup_expired_exports")
def cleanup_expired_exports():
    """
    만료된 Export ZIP 파일 자동 정리.
    Celery Beat에 등록하여 주기적으로 실행.
    """
    export_dir = os.path.join(settings.MEDIA_ROOT, EXPORT_BASE_DIR)
    if not os.path.exists(export_dir):
        return {"deleted": 0}

    now = time.time()
    deleted = 0

    for filename in os.listdir(export_dir):
        filepath = os.path.join(export_dir, filename)
        if not filename.endswith(".zip"):
            continue

        file_age = now - os.path.getmtime(filepath)
        if file_age > EXPORT_FILE_EXPIRE_SECONDS:
            os.remove(filepath)
            deleted += 1
            logger.info("만료 Export 삭제: %s (age=%ds)", filename, int(file_age))

    return {"deleted": deleted}
