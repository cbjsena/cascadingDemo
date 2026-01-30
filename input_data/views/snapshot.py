from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.apps import apps
from django.views.decorators.http import require_POST

from input_data.models import InputDataSnapshot
from common import messages as msg
from .common import MENU_STRUCTURE


@login_required
def snapshot_list(request):
    snapshots = InputDataSnapshot.objects.all().order_by('-created_at')

    # 기본값 생성 로직 (Helper)
    today_str = timezone.now().strftime('%Y%m%d')
    last_snapshot = InputDataSnapshot.objects.filter(data_id__startswith=today_str).order_by('-data_id').first()
    new_seq = 1
    if last_snapshot:
        try:
            new_seq = int(last_snapshot.data_id[8:]) + 1
        except ValueError:
            pass
    default_data_id = f"{today_str}{new_seq:02d}"
    default_base_ym = timezone.now().strftime('%Y%m')

    context = {
        "menu_structure": MENU_STRUCTURE,
        "snapshots": snapshots,
        "default_data_id": default_data_id,
        "default_base_ym": default_base_ym,
    }
    return render(request, 'input_data/snapshot_list.html', context)


@login_required
@transaction.atomic
def snapshot_create(request):
    if request.method == "POST":
        new_data_id = request.POST.get("data_id")
        source_data_id = request.POST.get("source_data_id")
        description = request.POST.get("description")
        base_ym = request.POST.get("base_year_month")

        if InputDataSnapshot.objects.filter(data_id=new_data_id).exists():
            messages.error(request, msg.SNAPSHOT_ID_DUPLICATE.format(data_id=new_data_id))
            return redirect("input_data:snapshot_list")

        new_snapshot = InputDataSnapshot.objects.create(
            data_id=new_data_id,
            description=description,
            base_year_month=base_ym,
            created_by=request.user,
            updated_by=request.user
        )

        if source_data_id:
            try:
                _clone_snapshot_data(source_data_id, new_snapshot)
                messages.success(request,
                                 msg.SNAPSHOT_CLONE_SUCCESS.format(data_id=new_data_id, source_id=source_data_id))
            except Exception as e:
                messages.error(request, msg.SNAPSHOT_CLONE_ERROR.format(error=str(e)))
                return redirect("input_data:snapshot_list")
        else:
            messages.success(request, msg.SNAPSHOT_CREATE_SUCCESS.format(data_id=new_data_id))

        return redirect("input_data:snapshot_list")
    return redirect("input_data:snapshot_list")


@login_required
@transaction.atomic
@require_POST
def snapshot_delete(request, data_id):
    snapshot = get_object_or_404(InputDataSnapshot, data_id=data_id)
    if not (snapshot.created_by == request.user or request.user.is_superuser):
        messages.error(request, msg.PERMISSION_DENIED)
        return redirect("input_data:snapshot_list")

    try:
        snapshot.delete()
        messages.success(request, msg.SNAPSHOT_DELETE_SUCCESS.format(data_id=data_id))
    except Exception as e:
        messages.error(request, msg.SNAPSHOT_DELETE_ERROR.format(error=str(e)))
    return redirect("input_data:snapshot_list")


def _clone_snapshot_data(source_id, target_snapshot):
    app_config = apps.get_app_config('input_data')
    models_to_clone = [m for m in app_config.get_models() if m.__name__ != 'InputDataSnapshot']

    for model_class in models_to_clone:
        original_objects = model_class.objects.filter(data_id=source_id)
        if original_objects.exists():
            new_objects = []
            for obj in original_objects:
                obj.pk = None
                obj.data_id = target_snapshot
                new_objects.append(obj)
            model_class.objects.bulk_create(new_objects)