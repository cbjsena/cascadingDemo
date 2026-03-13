from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from common.utils.date_utils import get_timeline_weeks
from input_data.models import (
    LaneProformaMapping,
    ProformaSchedule,
    ScenarioInfo,
)


@login_required
def lane_proforma_mapping(request):
    """
    Lane Proforma Mapping 편집 화면 (Creation > Schedule > Lane Proforma Mapping)
    """
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")
    scenario_id = request.GET.get("scenario_id")

    if request.method == "POST":
        scenario_id = request.POST.get("scenario_id")

        try:
            scenario = get_object_or_404(ScenarioInfo, id=scenario_id)

            with transaction.atomic():
                LaneProformaMapping.objects.filter(scenario=scenario).delete()

                selected_ids = request.POST.getlist("selected_proformas")
                for pid_str in selected_ids:
                    proforma_id = int(pid_str)
                    proforma = ProformaSchedule.objects.get(
                        id=proforma_id, scenario=scenario
                    )
                    LaneProformaMapping.objects.create(
                        scenario=scenario,
                        lane_id=proforma.lane_id,
                        proforma=proforma,
                        is_active=True,
                        created_by=request.user,
                        updated_by=request.user,
                    )

            messages.success(request, "Lane Proforma Mapping saved successfully.")
            return redirect(f"/input/lane-proforma-mapping/?scenario_id={scenario_id}")
        except Exception as e:
            messages.error(request, f"Save failed: {str(e)}")

    scenario_obj, mapping_data, timeline_weeks = _build_mapping_data(scenario_id)

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.CREATION,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.LANE_PROFORMA_MAPPING,
        "scenarios": scenarios,
        "selected_scenario_id": scenario_id,
        "scenario": scenario_obj,
        "mapping_data": mapping_data,
        "timeline_weeks": timeline_weeks,
        "is_readonly": False,
    }

    return render(request, "input_data/lane_proforma_mapping.html", context)


@login_required
def lane_proforma_list(request):
    """
    Lane Proforma Mapping 조회 화면 (Input Management > Schedule > Lane Proforma Mapping)
    편집 화면과 동일한 형식이지만 읽기 전용.
    """
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")
    scenario_id = request.GET.get("scenario_id")

    scenario_obj, mapping_data, timeline_weeks = _build_mapping_data(scenario_id)

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.LANE_PROFORMA_LIST,
        "scenarios": scenarios,
        "selected_scenario_id": scenario_id,
        "scenario": scenario_obj,
        "mapping_data": mapping_data,
        "timeline_weeks": timeline_weeks,
        "is_readonly": True,
    }

    return render(request, "input_data/lane_proforma_mapping.html", context)


def _build_mapping_data(scenario_id):
    """
    Lane Proforma Mapping 데이터 구성 (편집/조회 공통)
    Returns: (scenario_obj, mapping_data, timeline_weeks)
    """
    mapping_data = []
    scenario_obj = None
    timeline_weeks = []

    if not scenario_id:
        return scenario_obj, mapping_data, timeline_weeks

    try:
        scenario_obj = ScenarioInfo.objects.get(id=scenario_id)
    except ScenarioInfo.DoesNotExist:
        return scenario_obj, mapping_data, timeline_weeks

    if scenario_obj and scenario_obj.base_year_week:
        timeline_weeks = get_timeline_weeks(
            scenario_obj.base_year_week, scenario_obj.planning_horizon_months
        )

    proformas = ProformaSchedule.objects.filter(scenario_id=scenario_id).order_by(
        "lane_id", "effective_from_date", "proforma_name"
    )

    lane_proformas = {}
    for pf in proformas:
        if pf.lane_id not in lane_proformas:
            lane_proformas[pf.lane_id] = []
        lane_proformas[pf.lane_id].append(pf)

    existing_mapping_ids = set(
        LaneProformaMapping.objects.filter(scenario_id=scenario_id).values_list(
            "proforma_id", flat=True
        )
    )

    for lane_code in sorted(lane_proformas.keys()):
        pf_list = lane_proformas[lane_code]

        pf_infos = []
        for pf in pf_list:
            is_selected = pf.id in existing_mapping_ids
            pf_start = None
            pf_end = None
            if pf.effective_from_date:
                pf_start = (
                    pf.effective_from_date.date()
                    if hasattr(pf.effective_from_date, "date")
                    else pf.effective_from_date
                )
            if pf.effective_to_date:
                pf_end = (
                    pf.effective_to_date.date()
                    if hasattr(pf.effective_to_date, "date")
                    else pf.effective_to_date
                )
            pf_infos.append(
                {
                    "proforma": pf,
                    "is_selected": is_selected,
                    "pf_start": pf_start,
                    "pf_end": pf_end,
                }
            )

        selected_sorted = sorted(
            [info for info in pf_infos if info["is_selected"] and info["pf_start"]],
            key=lambda x: x["pf_start"],
        )
        effective_cutoff = {}
        for idx, sel in enumerate(selected_sorted):
            pf_id = sel["proforma"].id
            if idx + 1 < len(selected_sorted):
                next_start = selected_sorted[idx + 1]["pf_start"]
                cutoff = next_start - timedelta(days=1)
                if sel["pf_end"] and sel["pf_end"] < cutoff:
                    cutoff = sel["pf_end"]
                effective_cutoff[pf_id] = cutoff
            else:
                effective_cutoff[pf_id] = sel["pf_end"]

        pf_items = []
        for info in pf_infos:
            pf = info["proforma"]
            pf_start = info["pf_start"]
            pf_end = info["pf_end"]
            is_selected = info["is_selected"]

            pf_timeline = []
            pf_effective = []

            if timeline_weeks and pf_start:
                eff_end = effective_cutoff.get(pf.id, pf_end)
                for wk in timeline_weeks:
                    wk_start = wk["start_date"]
                    wk_end = wk_start + timedelta(days=6)
                    in_range = pf_start <= wk_end and (
                        pf_end is None or pf_end >= wk_start
                    )
                    in_effective = (
                        in_range
                        and pf_start <= wk_end
                        and (eff_end is None or eff_end >= wk_start)
                    )
                    pf_timeline.append(in_range)
                    pf_effective.append(in_effective)
            else:
                pf_timeline = [False] * len(timeline_weeks)
                pf_effective = [False] * len(timeline_weeks)

            cells = []
            for i in range(len(pf_timeline)):
                cells.append(
                    {
                        "in_range": pf_timeline[i],
                        "effective": pf_effective[i],
                    }
                )

            pf_items.append(
                {
                    "proforma": pf,
                    "is_selected": is_selected,
                    "cells": cells,
                }
            )

        mapping_data.append(
            {
                "lane_code": lane_code,
                "proforma_items": pf_items,
                "proforma_count": len(pf_list),
                "selected_count": sum(1 for p in pf_items if p["is_selected"]),
            }
        )

    return scenario_obj, mapping_data, timeline_weeks
