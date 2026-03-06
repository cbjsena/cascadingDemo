import csv
import os

ids = []
with open(
    "../../doc/test_scenarios/test_scenarios_input_data.csv", "r", encoding="utf-8-sig"
) as f:
    reader = csv.DictReader(f)
    for row in reader:
        ids.append(row["ID"].strip())

test_dirs = ["input_data/tests", "api/tests"]
all_content = ""
for td in test_dirs:
    for root, dirs, files in os.walk(td):
        for fn in files:
            if fn.endswith(".py"):
                with open(os.path.join(root, fn), "r", encoding="utf-8") as fh:
                    all_content += fh.read()

missing = [sid for sid in ids if sid not in all_content]
print(f"Total: {len(ids)} IDs, Missing: {len(missing)}")
for m in missing:
    print(f"  MISSING: {m}")
if not missing:
    print("All IDs found!")
