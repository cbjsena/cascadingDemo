from common.menus import CREATION_MENU_STRUCTURE, MASTER_MENU_STRUCTURE, MENU_STRUCTURE


def global_menus(request):
    """모든 템플릿에 전체 메뉴 구조를 자동 전달"""
    return {
        "master_menu_structure": MASTER_MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "menu_structure": MENU_STRUCTURE,
    }
