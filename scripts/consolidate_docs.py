import glob
import os

docs_dir = r"c:\Users\md200\OneDrive\Desktop\OneMove\docs"
arch_dir = os.path.join(docs_dir, "architecture")
sys_dir = os.path.join(docs_dir, "system")

files_to_merge = [
    os.path.join(docs_dir, "TECHNICAL_ARCHITECTURE_OVERVIEW.md"),
    os.path.join(docs_dir, "ARCHITECTURE.md"),
    os.path.join(arch_dir, "ZONEPILOT_SYSTEM_ARCHITECTURE.md"),
    os.path.join(docs_dir, "DECISIONS.md")
]

merged_content = "# OneMove System Architecture & Decisions\n\n"
merged_content += "This document consolidates the technical architecture for the OneMove super-app and the ZonePilot deterministic optimization engine.\n\n"

for fpath in files_to_merge:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            merged_content += f.read() + "\n\n"
        print(f"Read {fpath}")

# Add ADR log
merged_content += "## Architecture Decision Records (ADRs)\n\n"
merged_content += "The following ADRs log significant architectural decisions made during development. They are located in `docs/system/`:\n\n"

adr_files = sorted(glob.glob(os.path.join(sys_dir, "ADR-*.md")))
for adr in adr_files:
    basename = os.path.basename(adr)
    name = basename.replace(".md", "").replace("_", " ")
    merged_content += f"- [{name}](../system/{basename})\n"

out_path = os.path.join(arch_dir, "SYSTEM_ARCHITECTURE.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(merged_content)

print(f"Wrote consolidated architecture to {out_path}")

# Now delete the old ones
files_to_delete = files_to_merge + [
    os.path.join(docs_dir, "README_PORTFOLIO_VERSION.md")
]

for fpath in files_to_delete:
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"Deleted {fpath}")

