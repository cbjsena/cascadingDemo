from django.core.management.base import BaseCommand

from input_data.services.scenario_service import create_scenario_from_base


class Command(BaseCommand):
    help = "Create a default scenario from base data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--description",
            type=str,
            default="Base scenario created from initial data",
            help="Description for the default scenario",
        )
        parser.add_argument(
            "--base-year-week",
            type=str,
            default=None,
            help="Base year week (YYYY-WXX format)",
        )

    def handle(self, *args, **kwargs):
        description = kwargs["description"]
        base_year_week = kwargs.get("base_year_week")

        self.stdout.write(
            self.style.MIGRATE_HEADING("Creating Default Scenario from Base Data")
        )

        try:
            # 서비스 호출 (새로운 시그니처 사용)
            scenario, summary = create_scenario_from_base(
                description=description, base_year_week=base_year_week
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Scenario '{scenario.code}' (ID: {scenario.id}) created successfully."
                )
            )

            # 요약 정보 출력
            for table, count in summary.items():
                self.stdout.write(f" - {table}: {count} rows")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed: {str(e)}"))
