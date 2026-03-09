from common.menus import MASTER_MENU_STRUCTURE


def master_menu(request):
    """모든 템플릿에 Master 메뉴 구조를 자동 전달"""
    return {
        "master_menu_structure": MASTER_MENU_STRUCTURE,
    }
