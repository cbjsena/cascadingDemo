from django.core.management.base import BaseCommand

from input_data.services.scenario_service import create_scenario_from_base


class Command(BaseCommand):
    help = "Create a default scenario from Base data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            default="Base Scenario",
            help="Name for the default scenario",
        )
        parser.add_argument(
            "--description",
            type=str,
            default="Base scenario created from initial data",
            help="Description for the default scenario",
        )

    def handle(self, *args, **kwargs):
        scenario_name = kwargs["name"]
        description = kwargs["description"]

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Creating Default Scenario: '{scenario_name}'")
        )

        try:
            # 서비스 호출 (새로운 시그니처 사용)
            scenario, summary = create_scenario_from_base(scenario_name, description)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Scenario '{scenario_name}' (ID: {scenario.id}) created successfully."
                )
            )

            # 요약 정보 출력
            for table, count in summary.items():
                self.stdout.write(f" - {table}: {count} rows")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed: {str(e)}"))
