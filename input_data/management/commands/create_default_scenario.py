from django.core.management.base import BaseCommand

from common import messages as msg
from input_data.services.scenario_service import create_scenario_from_base


class Command(BaseCommand):
    help = "Create a default scenario from Base data"

    def add_arguments(self, parser):
        parser.add_argument("--scenario_id", type=str, default="202601_BASE")

    def handle(self, *args, **kwargs):
        target_id = kwargs["scenario_id"]
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Creating Default Scenario: {target_id}")
        )

        try:
            # 서비스 호출
            scenario, summary = create_scenario_from_base(target_id)

            self.stdout.write(
                self.style.SUCCESS(
                    msg.SCENARIO_CREATE_SUCCESS.format(scenario_id=target_id)
                )
            )

            # 요약 정보 출력
            for table, count in summary.items():
                self.stdout.write(f" - {table}: {count} rows")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed: {str(e)}"))
