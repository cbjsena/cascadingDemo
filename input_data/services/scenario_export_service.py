"""
시나리오 하위 전체 데이터를 모델별 JSON 파일로 Export하고 ZIP으로 압축.

동작 순서:
  1. scenario FK가 있는 모델을 동적 탐색 (_clone_scenario_data 패턴 재사용)
  2. DjangoJSONEncoder로 직렬화
  3. scenario_{id}/ 폴더에 모델별 .json 파일 생성
  4. ZIP 압축 → scenario_{id}_data.zip
"""

import json
import logging
import os
import shutil
from datetime import datetime, timedelta

from django.apps import apps
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from common.constants import DAYS
from input_data.models import ScenarioInfo
from input_data.services.export_configs import (
    EXPORT_BASE_DIR,
    EXPORT_EXCLUDE_FIELDS,
    EXPORT_EXCLUDE_MODELS,
    EXPORT_MODEL_OPTIONS,
    MODEL_EXPORT_ORDER,
    PROFORMA_EXPORT_FILENAME,
    PROFORMA_PORT_ROTATION_FIELDS,
    PROFORMA_VERSION_FIELDS,
    PROFORMA_VESSEL_POSITION_FIELDS,
    ZIP_FILENAME_PATTERN,
)

logger = logging.getLogger(__name__)


class ScenarioExportService:
    """시나리오 하위 전체 데이터를 모델별 JSON 파일로 Export + ZIP 압축"""

    def __init__(self, scenario_id, base_dir=None):
        self.scenario = ScenarioInfo.objects.get(id=scenario_id)
        self.scenario_id = scenario_id
        self.base_dir = base_dir or os.path.join(settings.MEDIA_ROOT, EXPORT_BASE_DIR)
        self.output_dir = os.path.join(self.base_dir, str(scenario_id))
        self.zip_path = None

    def export_all(self, progress_callback=None):
        """
        전체 Export 실행.

        Args:
            progress_callback: 진행률 콜백 함수 (percent, step_text)
                               Celery task에서 update_state를 전달.

        Returns:
            {
                'meta': { ... },
                'files': {'_meta.json': 1, 'proforma_schedule.json': 15, ...},
                'total_records': 128,
                'zip_path': '/media/exports/scenarios/scenario_42_data.zip',
            }
        """
        if progress_callback is None:
            progress_callback = lambda pct, step: None  # noqa: E731

        # 기존 폴더가 있으면 제거 후 재생성
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        file_summary = {}
        total_records = 0

        # ── 1. 메타 정보 Export ──
        progress_callback(5, "메타 정보 생성 중...")
        meta_data = self._build_meta()
        self._write_json("_meta.json", meta_data)
        file_summary["_meta.json"] = 1

        # ── 2. 모델 동적 탐색 ──
        progress_callback(10, "모델 탐색 중...")
        master_models = self._discover_scenario_models()
        logger.info(
            "Export 대상 모델 %d개: %s",
            len(master_models),
            [m.__name__ for m in master_models],
        )
        meta_data["exported_models"] = [m.__name__ for m in master_models]

        # ── 3. 모델별 Export ──
        model_count = len(master_models)
        for idx, model_class in enumerate(master_models):
            pct = 15 + int((idx / max(model_count, 1)) * 70)
            progress_callback(pct, f"{model_class.__name__} 추출 중...")

            file_name = self._model_to_filename(model_class)
            records = self._serialize_model(model_class)

            if records:
                self._write_json(file_name, records)
                file_summary[file_name] = len(records)
                total_records += len(records)
                logger.info("  %s: %d records", file_name, len(records))

            # Detail 모델도 Export
            detail_results = self._export_detail_models(model_class)
            for detail_file, detail_count in detail_results.items():
                file_summary[detail_file] = detail_count
                total_records += detail_count

        # ── 3-1. Proforma 통합 Export ──
        progress_callback(85, "Proforma 통합 Export 중...")
        proforma_count = self._export_proforma_unified()
        if proforma_count > 0:
            file_summary[PROFORMA_EXPORT_FILENAME] = proforma_count
            total_records += proforma_count
            meta_data["exported_models"].append(
                "Proforma (ProformaSchedule + Detail + VesselPosition + LaneMapping)"
            )
            logger.info("  %s: %d records", PROFORMA_EXPORT_FILENAME, proforma_count)

        # ── 4. _meta.json 갱신 (exported_models 포함) ──
        meta_data["total_records"] = total_records
        meta_data["files"] = file_summary
        self._write_json("_meta.json", meta_data)

        # ── 5. ZIP 압축 ──
        progress_callback(90, "ZIP 압축 중...")
        self.zip_path = self._create_zip()

        progress_callback(100, "완료")
        logger.info(
            "Export 완료: scenario=%s, files=%d, records=%d, zip=%s",
            self.scenario.code,
            len(file_summary),
            total_records,
            self.zip_path,
        )

        return {
            "meta": meta_data,
            "files": file_summary,
            "total_records": total_records,
            "zip_path": self.zip_path,
        }

    # ════════════════════════════════════════════════════════════
    # 모델 탐색
    # ════════════════════════════════════════════════════════════

    def _discover_scenario_models(self):
        """
        scenario FK가 있는 모델을 동적 탐색.
        _clone_scenario_data와 동일한 패턴으로 Master 모델만 추출.
        Detail 모델은 Master Export 시 자동 처리.
        """
        app_config = apps.get_app_config("input_data")

        all_models = []
        for m in app_config.get_models():
            if m.__name__ in EXPORT_EXCLUDE_MODELS:
                continue
            # scenario FK 존재 여부 확인
            has_scenario_fk = any(
                f.name == "scenario" and f.is_relation for f in m._meta.fields
            )
            if has_scenario_fk:
                all_models.append(m)

        # Detail 모델 식별
        detail_model_set = set()
        for m in all_models:
            for rel in m._meta.related_objects:
                if isinstance(rel, models.ManyToOneRel) and "details" in (
                    rel.related_name or ""
                ):
                    detail_model_set.add(rel.related_model)

        # Master만 추출 (Detail은 Master Export 시 자동 처리)
        master_models = [m for m in all_models if m not in detail_model_set]

        # 정렬
        master_models.sort(key=lambda m: MODEL_EXPORT_ORDER.get(m.__name__, 99))
        return master_models

    def _get_detail_rels(self, master_model):
        """Master 모델에 연결된 Detail 관계 목록 반환"""
        return [
            rel
            for rel in master_model._meta.related_objects
            if isinstance(rel, models.ManyToOneRel)
            and "details" in (rel.related_name or "")
        ]

    # ════════════════════════════════════════════════════════════
    # 직렬화 (DjangoJSONEncoder)
    # ════════════════════════════════════════════════════════════

    def _serialize_model(self, model_class):
        """모델 queryset을 DjangoJSONEncoder 호환 dict 리스트로 변환
        - BunkerPrice: trade 필드 제거, lane별 min price만 export
        """
        from django.db.models import Min

        options = EXPORT_MODEL_OPTIONS.get(model_class.__name__, {})
        exclude_fields = set(options.get("exclude_fields", []))
        order_by = options.get("order_by", ["pk"])

        # Special logic for BunkerPrice
        if model_class.__name__ == "BunkerPrice":
            # Group by (base_year_month, lane_id, bunker_type), get min price
            qs = (
                model_class.objects.filter(scenario_id=self.scenario_id)
                .values("base_year_month", "lane_id", "bunker_type")
                .annotate(min_price=Min("bunker_price"))
            )
            # Get the pk of the min price record for each group
            min_price_pks = set()
            for row in qs:
                obj = (
                    model_class.objects.filter(
                        scenario_id=self.scenario_id,
                        base_year_month=row["base_year_month"],
                        lane_id=row["lane_id"],
                        bunker_type=row["bunker_type"],
                        bunker_price=row["min_price"],
                    )
                    .order_by("pk")
                    .first()
                )
                if obj:
                    min_price_pks.add(obj.pk)
            # Only export those records, and exclude trade field
            qs = model_class.objects.filter(pk__in=min_price_pks).order_by(*order_by)
            # Add 'trade' to exclude_fields
            exclude_fields.add("trade")
        else:
            qs = model_class.objects.filter(scenario_id=self.scenario_id).order_by(
                *order_by
            )

        # FK 필드 select_related (N+1 방지)
        fk_fields = [
            f.name
            for f in model_class._meta.fields
            if f.is_relation and f.name not in ("id", "scenario")
        ]
        if fk_fields:
            qs = qs.select_related(*fk_fields)

        return [
            self._obj_to_dict(obj, model_class.__name__, exclude_fields) for obj in qs
        ]

    def _serialize_detail_model(self, detail_model, fk_field_name, master_pks):
        """Detail 모델 queryset 직렬화"""
        options = EXPORT_MODEL_OPTIONS.get(detail_model.__name__, {})
        exclude_fields = set(options.get("exclude_fields", []))
        order_by = options.get("order_by", ["pk"])

        qs = detail_model.objects.filter(
            **{f"{fk_field_name}__in": master_pks}
        ).order_by(*order_by)

        return [
            self._obj_to_dict(obj, detail_model.__name__, exclude_fields) for obj in qs
        ]

    def _obj_to_dict(self, obj, model_name, exclude_fields=None):
        """
        모델 인스턴스를 dict로 변환.
        - scenario FK 제외 (Import 시 대상 시나리오로 재설정)
        - id, created_at/by, updated_at/by 등 공통 필드 제외
        - field_map: DB attname → 사용자 친화적 key 매핑
        - nesting: 여러 필드를 하나의 중첩 객체로 그룹핑
        """
        if exclude_fields is None:
            exclude_fields = set()

        options = EXPORT_MODEL_OPTIONS.get(model_name, {})
        field_map = options.get("field_map", {})
        nesting = options.get("nesting", {})

        # 1단계: 필드 추출 + rename
        flat_data = {}
        for field in obj._meta.fields:
            if field.name == "scenario":
                continue
            if (
                field.name in EXPORT_EXCLUDE_FIELDS
                or field.attname in EXPORT_EXCLUDE_FIELDS
            ):
                continue
            if field.name in exclude_fields:
                continue

            # field_map에서 attname을 우선 조회, 없으면 attname 그대로
            json_key = field_map.get(field.attname, field.attname)
            if json_key is None:
                continue  # None이면 제외
            flat_data[json_key] = getattr(obj, field.attname)

        # 2단계: nesting 적용
        if nesting:
            for group_key, member_keys in nesting.items():
                group = {}
                for mk in member_keys:
                    if mk in flat_data:
                        group[mk] = flat_data.pop(mk)
                if group:
                    flat_data[group_key] = group

        return flat_data

    # ════════════════════════════════════════════════════════════
    # Detail Export
    # ════════════════════════════════════════════════════════════

    def _export_detail_models(self, master_model):
        """Master에 연결된 Detail 모델들을 Export. {filename: count} 반환"""
        results = {}
        detail_rels = self._get_detail_rels(master_model)

        if not detail_rels:
            return results

        master_pks = list(
            master_model.objects.filter(scenario_id=self.scenario_id).values_list(
                "pk", flat=True
            )
        )

        if not master_pks:
            return results

        for rel in detail_rels:
            detail_model = rel.related_model
            fk_field_name = rel.remote_field.name

            records = self._serialize_detail_model(
                detail_model, fk_field_name, master_pks
            )

            if records:
                file_name = self._model_to_filename(detail_model)
                self._write_json(file_name, records)
                results[file_name] = len(records)
                logger.info("  %s (detail): %d records", file_name, len(records))

        return results

    # ════════════════════════════════════════════════════════════
    # Proforma 통합 Export (service_lanes → versions → port_rotation)
    # ════════════════════════════════════════════════════════════

    def _export_proforma_unified(self):
        """
        ProformaSchedule, ProformaScheduleDetail, CascadingVesselPosition,
        LaneProformaMapping을 하나의 proforma.json으로 통합 Export.

        구조:
        {
          "service_lanes": [
            {
              "lane_code": "AEX",
              "versions": [
                {
                  "version_code": "0001",
                  ...(ProformaSchedule fields)...,
                  "vessel_positions": [...],
                  "port_rotation": [
                    { ...(ProformaScheduleDetail fields)... }
                  ]
                }
              ]
            }
          ]
        }
        """
        from input_data.models import (
            CascadingVesselPosition,
            LaneProformaMapping,
            ProformaSchedule,
            ProformaScheduleDetail,
        )

        # 1. ProformaSchedule 조회
        proformas = (
            ProformaSchedule.objects.filter(scenario_id=self.scenario_id)
            .select_related("lane")
            .order_by("lane_id", "proforma_name")
        )

        if not proformas.exists():
            return 0

        # 2. Detail, VesselPosition, LaneMapping 미리 조회 (N+1 방지)
        proforma_pks = list(proformas.values_list("pk", flat=True))

        details_by_proforma = {}
        for detail in (
            ProformaScheduleDetail.objects.filter(proforma_id__in=proforma_pks)
            .select_related("port")
            .order_by("proforma_id", "calling_port_seq")
        ):
            details_by_proforma.setdefault(detail.proforma_id, []).append(detail)

        positions_by_proforma = {}
        for pos in CascadingVesselPosition.objects.filter(
            scenario_id=self.scenario_id, proforma_id__in=proforma_pks
        ).order_by("proforma_id", "vessel_position"):
            positions_by_proforma.setdefault(pos.proforma_id, []).append(pos)

        mapping_by_proforma = {}
        for mapping in LaneProformaMapping.objects.filter(
            scenario_id=self.scenario_id, proforma_id__in=proforma_pks
        ):
            mapping_by_proforma[mapping.proforma_id] = mapping

        # 3. Lane 기준으로 그룹핑
        lanes_dict = {}  # lane_code → list of proformas
        for pf in proformas:
            lanes_dict.setdefault(pf.lane_id, []).append(pf)

        # 4. 계층 구조 생성
        total_records = 0
        service_lanes = []

        for lane_code, lane_proformas in lanes_dict.items():
            versions = []
            for pf in lane_proformas:
                version_data = self._proforma_to_dict(pf)

                # is_active from LaneProformaMapping
                mapping = mapping_by_proforma.get(pf.pk)
                if mapping:
                    version_data["is_active"] = mapping.is_active
                details = details_by_proforma.get(pf.pk, [])

                # anchor_date 계산 및 주입
                effective_from = getattr(pf, "effective_from_date", None)
                anchor_date = None

                for detail in details:
                    # 조건: port_set_seq가 1이고 첫 포지션(port_seq가 1)인 포트 탐색
                    if getattr(detail, "calling_port_seq", None) == 1:
                        day_code = getattr(detail, "etb_day_code", None)
                        time_str = getattr(detail, "etb_day_time", "0000")
                        anchor_date = self._calculate_anchor_date(
                            effective_from, day_code, time_str
                        )
                        break  # 찾았으므로 루프 종료

                version_data["anchor_date"] = anchor_date

                # vessel_positions
                positions = positions_by_proforma.get(pf.pk, [])
                version_data["vessel_positions"] = [
                    self._vessel_position_to_dict(pos) for pos in positions
                ]

                # port_rotation
                version_data["port_rotation"] = [
                    self._port_rotation_to_dict(detail) for detail in details
                ]

                total_records += 1 + len(positions) + len(details)
                versions.append(version_data)

            service_lanes.append(
                {
                    "lane_code": lane_code,
                    "versions": versions,
                }
            )

        data = {"service_lanes": service_lanes}
        self._write_json(PROFORMA_EXPORT_FILENAME, data)
        return total_records

    def _proforma_to_dict(self, pf):
        """ProformaSchedule 인스턴스를 dict로 변환 (PROFORMA_VERSION_FIELDS 적용)"""
        cfg = PROFORMA_VERSION_FIELDS
        exclude = cfg.get("exclude", set())
        field_map = cfg.get("field_map", {})
        result = {}
        for field in pf._meta.fields:
            if field.attname in exclude or field.name in exclude:
                continue

            json_key = field_map.get(field.attname, field.attname)
            if json_key is None:
                continue
            result[json_key] = getattr(pf, field.attname)
        return result

    def _port_rotation_to_dict(self, detail):
        """ProformaScheduleDetail 인스턴스를 dict로 변환 (field_map + nesting 적용)"""
        cfg = PROFORMA_PORT_ROTATION_FIELDS
        exclude = cfg.get("exclude", set())
        field_map = cfg.get("field_map", {})
        nesting = cfg.get("nesting", {})

        result = {}
        for field in detail._meta.fields:
            if field.attname in exclude or field.name in exclude:
                continue

            json_key = field_map.get(field.attname, field.attname)
            if json_key is None:
                continue
            val = getattr(detail, field.attname)
            if (
                json_key
                in ("pilot_in_minutes", "pilot_out_minutes", "sea_sailing_time")
                and val is not None
            ):
                try:
                    if json_key == "sea_sailing_time":
                        val = int(float(val))
                    else:
                        val = int(float(val) * 60)
                except (TypeError, ValueError):
                    val = None  # 또는 raise / logging 처리

            result[json_key] = val

        # nesting 적용
        for group_key, member_keys in nesting.items():
            group = {}
            for mk in member_keys:
                if mk in result:
                    group[mk] = result.pop(mk)
            if group:
                result[group_key] = group

        return result

    def _vessel_position_to_dict(self, pos):
        """CascadingVesselPosition 인스턴스를 dict로 변환"""
        exclude = PROFORMA_VESSEL_POSITION_FIELDS.get("exclude", set())
        result = {}
        for field in pos._meta.fields:
            if field.attname in exclude or field.name in exclude:
                continue
            result[field.attname] = getattr(pos, field.attname)
        return result

    def _calculate_anchor_date(self, effective_from, day_code, time_str):
        """
        effective_from 날짜 이후 가장 먼저 도래하는 day_code(요일)의 정확한 날짜와 시간을 계산합니다.
        """
        if not effective_from or not day_code:
            return None

        try:
            # effective_from이 문자열인 경우 date 객체로 변환
            if isinstance(effective_from, str):
                eff_date = datetime.strptime(effective_from, "%Y-%m-%d").date()
            else:
                eff_date = effective_from

            day_str = str(day_code).upper()[:3]
            if day_str not in DAYS:
                return None

            # DAYS 리스트 상의 목표 요일 인덱스 (SUN=0, MON=1, ..., SAT=6)
            target_index = DAYS.index(day_str)

            # Python weekday() (MON=0, ..., SUN=6)를 DAYS 인덱스 체계에 맞게 변환
            current_index = (eff_date.weekday() + 1) % 7

            # 목표 요일까지 남은 일수 계산
            days_ahead = target_index - current_index
            if days_ahead < 0:
                days_ahead += 7

            anchor_date = eff_date + timedelta(days=days_ahead)

            # 3. 시간 포맷팅 (HHMM -> HH:MM:00)
            if time_str:
                # 공백 제거 및 4자리 보장 (예: '930' -> '0930')
                clean_time = str(time_str).strip().zfill(4)
                if len(clean_time) >= 4:
                    time_part = f"{clean_time[:2]}:{clean_time[2:4]}:00"
                else:
                    time_part = "00:00:00"
            else:
                time_part = "00:00:00"

            # 결합하여 반환 (예: "2026-01-07 14:00:00")
            return f"{anchor_date.strftime('%Y-%m-%d')} {time_part}"
        except Exception:
            return None

    # ════════════════════════════════════════════════════════════
    # 메타 정보
    # ════════════════════════════════════════════════════════════

    def _build_meta(self):
        """시나리오 메타 정보 dict 생성"""
        s = self.scenario
        return {
            "scenario_id": s.id,
            "code": s.code,
            "description": s.description,
            "base_year_week": s.base_year_week,
            "scenario_type": s.scenario_type,
            "planning_horizon_months": s.planning_horizon_months,
            "tags": s.tags,
            "base_scenario_id": s.base_scenario_id,
            "status": s.status,
            "created_at": s.created_at,
            "created_by": str(s.created_by) if s.created_by else None,
            "exported_at": datetime.now(),
            "exported_models": [],
        }

    # ════════════════════════════════════════════════════════════
    # 파일 I/O
    # ════════════════════════════════════════════════════════════

    def _write_json(self, file_name, data):
        """JSON 파일 작성. DjangoJSONEncoder 사용."""
        file_path = os.path.join(self.output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)

    def _create_zip(self):
        """output_dir를 ZIP으로 압축. 반환값: ZIP 파일 절대 경로"""
        zip_name = ZIP_FILENAME_PATTERN.format(scenario_id=self.scenario_id)
        zip_base = os.path.join(self.base_dir, zip_name.replace(".zip", ""))

        zip_path = shutil.make_archive(
            base_name=zip_base,
            format="zip",
            root_dir=self.output_dir,
        )
        logger.info("ZIP 생성 완료: %s", zip_path)
        return zip_path

    # ════════════════════════════════════════════════════════════
    # 유틸리티
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _model_to_filename(model_class):
        """모델 클래스의 db_table 이름을 파일명으로 사용. 예: sce_cost_canal_fee.json"""
        return f"{model_class._meta.db_table}.json"

    def cleanup(self):
        """Export 폴더 및 ZIP 파일 정리"""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if self.zip_path and os.path.exists(self.zip_path):
            os.remove(self.zip_path)
