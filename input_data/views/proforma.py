from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from input_data.models import InputDataSnapshot
from input_data.services.proforma_service import ProformaService
from common import messages as msg
from common import constants as const

@login_required
def proforma_create(request):
    """Proforma Schedule 생성 View"""
    service = ProformaService()

    # 초기 컨텍스트
    context = {
        "snapshots": InputDataSnapshot.objects.all().order_by('-created_at'),
        "rows": [],
        "header": {},
        "days": const.DAYS,
    }

    if request.method == "POST":
        action = request.POST.get('action')

        # 1. 파싱 (모든 액션 공통)
        rows = service.parse_rows(request)
        header = service.parse_header(request)

        # 2. 액션 처리
        if action == "add_row":
            rows = service.add_row(rows, header.get('data_id'))

        elif action == "insert_row":
            try:
                idx = int(request.POST.get('selected_index', -1))
                rows = service.insert_row(rows, idx)
            except ValueError:
                pass  # 인덱스 없음/오류 무시

        elif action == "delete_row":
            indices = request.POST.getlist('row_check')
            rows = service.delete_rows(rows, indices)

        elif action == "new":
            rows = []
            # Header 정보는 유지할지 초기화할지 정책에 따름 (여기선 유지)
            messages.info(request, msg.SCHEDULE_NEW_STARTED)

        elif action == "calculate":
            # [기능] 계산만 수행하고 화면 갱신
            rows = service.calculate_schedule(rows, header)
            messages.info(request, msg.SCHEDULE_CALCULATED)

        elif action == "save":
            # [기능] 계산 수행 후 결과 저장
            # 1. 데이터 정합성을 위해 저장 전 한 번 더 계산
            rows = service.calculate_schedule(rows, header)

            try:
                # 2. DB 저장
                service.save_to_db(header, rows, request.user)
                messages.success(request, msg.SCHEDULE_SAVE_SUCCESS)
            except Exception as e:
                messages.error(request, msg.SCHEDULE_SAVE_ERROR.format(error=str(e)))

        elif action == "export":
            return redirect('input_data:proforma_export')

        elif action == "close":
            return redirect('input_data:input_home')

        context['rows'] = rows
        context['header'] = header

    return render(request, 'input_data/proforma_create.html', context)


@login_required
def proforma_export(request):
    # Export Logic Placeholder
    messages.info(request, msg.FUNC_NOT_IMPLEMENTED.format(func_name="Export"))
    return redirect('input_data:proforma_create')


@login_required
def proforma_upload(request):
    # Upload Logic Placeholder
    messages.info(request, msg.FUNC_NOT_IMPLEMENTED.format(func_name="Upload"))
    return redirect('input_data:proforma_create')


@login_required
def proforma_template_download(request):
    # Template Download Logic Placeholder
    messages.info(request, msg.FUNC_NOT_IMPLEMENTED.format(func_name="Template download"))
    return redirect('input_data:proforma_create')