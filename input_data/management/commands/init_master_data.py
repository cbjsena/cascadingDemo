import os

from django.apps import apps

from common import messages as msg

from ._base_loader import BaseDataLoader


class Command(BaseDataLoader):
    help = (
        "Load master_ table data from CSV files. "
        "WARNING: sce_ (via ScenarioInfo CASCADE) and base_ data will be deleted first "
        "because sce_/base_ tables reference master_ with PROTECT FK."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Skip confirmation prompt and execute immediately.",
        )

    def handle(self, *args, **kwargs):
        self._fk_cache = {}
        force = kwargs.get("force", False)

        base_data_dir = self.get_base_data_dir()
        if not base_data_dir:
            return

        if not os.path.exists(base_data_dir):
            self.stdout.write(
                self.style.ERROR(msg.DIR_NOT_FOUND.format(path=base_data_dir))
            )
            return

        app_config = apps.get_app_config("input_data")
        master_models = [
            m for m in app_config.get_models() if m._meta.db_table.startswith("master_")
        ]
        base_models = [
            m for m in app_config.get_models() if m._meta.db_table.startswith("base_")
        ]

        # 삭제 대상 건수 사전 조회
        from input_data.models import ScenarioInfo

        scenario_count = ScenarioInfo.objects.count()
        base_counts = {m._meta.db_table: m.objects.count() for m in base_models}
        master_counts = {m._meta.db_table: m.objects.count() for m in master_models}
        total_base = sum(base_counts.values())
        total_master = sum(master_counts.values())

        # 경고 메시지 출력
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(
            self.style.WARNING("  WARNING: init_master_data will DELETE ALL data below")
        )
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                f"  1) ScenarioInfo  : {scenario_count} scenario(s) "
                f"-> CASCADE deletes ALL sce_ table data"
            )
        )
        self.stdout.write(
            self.style.WARNING(f"  2) base_ tables  : {total_base} total row(s)")
        )
        for table, cnt in base_counts.items():
            if cnt:
                self.stdout.write(f"       {table}: {cnt}")
        self.stdout.write(
            self.style.WARNING(f"  3) master_ tables: {total_master} total row(s)")
        )
        for table, cnt in master_counts.items():
            if cnt:
                self.stdout.write(f"       {table}: {cnt}")

        self.stdout.write("")
        self.stdout.write(
            "  After deletion, only master_ tables will be reloaded from CSV."
        )
        self.stdout.write(
            "  You must run 'init_base_data' separately to reload base_ tables."
        )
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write("")

        # 확인 프롬프트
        if not force:
            answer = input("  Proceed? (yes/no): ").strip().lower()
            if answer not in ("yes", "y"):
                self.stdout.write(self.style.ERROR("  Aborted."))
                return

        self.stdout.write(self.style.MIGRATE_HEADING("[init_master_data] Starting..."))

        # 삭제 순서: sce_ (CASCADE) -> base_ -> master_
        self._delete_cascade_then_models(base_models, master_models)

        # 로드 순서: master_ 만
        self.load_models(master_models, base_data_dir)

        self.stdout.write(
            self.style.SUCCESS(
                "\n[init_master_data] Done. "
                "Run 'init_base_data' to reload base_ tables, "
                "then recreate scenarios as needed."
            )
        )

    def _delete_cascade_then_models(self, base_models, master_models):
        """
        master_ 를 안전하게 삭제하기 위한 순서:
          1) ScenarioInfo 삭제 -> CASCADE 로 모든 sce_ 자동 삭제
          2) base_ 삭제 (master_ 를 PROTECT FK 로 참조)
          3) master_ 삭제
        """
        from input_data.models import ScenarioInfo

        # 1) sce_ 전체 삭제
        sce_count, _ = ScenarioInfo.objects.all().delete()
        if sce_count:
            self.stdout.write(
                self.style.WARNING(
                    f"  -> Cleared ScenarioInfo and {sce_count} related row(s) "
                    f"via CASCADE"
                )
            )

        # 2) base_ 삭제
        self.delete_models(base_models)

        # 3) master_ 삭제
        self.delete_models(master_models)
