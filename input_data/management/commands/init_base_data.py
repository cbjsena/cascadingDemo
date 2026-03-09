import os

from django.apps import apps

from common import messages as msg

from ._base_loader import BaseDataLoader


class Command(BaseDataLoader):
    help = "Load base_ table data from CSV files (sce_, master_ unaffected)"

    def handle(self, *args, **kwargs):
        self._fk_cache = {}

        base_data_dir = self.get_base_data_dir()
        if not base_data_dir:
            return

        if not os.path.exists(base_data_dir):
            self.stdout.write(
                self.style.ERROR(msg.DIR_NOT_FOUND.format(path=base_data_dir))
            )
            return

        app_config = apps.get_app_config("input_data")
        base_models = [
            m for m in app_config.get_models() if m._meta.db_table.startswith("base_")
        ]

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "[init_base_data] Loading base_ tables only "
                "(sce_ and master_ are NOT affected)"
            )
        )

        # base_ -> master_ FK는 없으므로 base_만 삭제/로드하면 됨
        self.delete_models(base_models)
        self.load_models(base_models, base_data_dir)
