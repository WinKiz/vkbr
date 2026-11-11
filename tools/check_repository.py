"""Checks SDD artifacts and contract examples, not BSL execution. Standard library only."""
from pathlib import Path
from datetime import date, timedelta
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    required = [
        "README.md", "AGENTS.md", ".specify/memory/constitution.md",
        "docs/project-context.md", "docs/roadmap.md", "docs/status.md",
        "docs/traceability.md", "docs/decisions.md", "docs/baseline/source-manifest.json",
        "specs/001-request-validation/spec.md", "specs/001-request-validation/plan.md",
        "specs/001-request-validation/tasks.md", "src/README.md",
        "src/CommonModules/CSAPIRequestValidation/Ext/Module.bsl",
        "tests/1c/CSAPIRequestValidationTests.bsl",
    ]
    for name in required:
        path = ROOT / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise ValueError(f"Missing or empty artifact: {name}")
    for path in ROOT.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                raise ValueError(f"Broken relative link in {path.relative_to(ROOT)}: {target}")
    ns = {"m": "http://v8.1c.ru/8.3/MDClasses"}
    for path in [ROOT / "src/CommonModules/CSAPIRequestValidation.xml",
                 ROOT / "tests/1c/CSAPIRequestValidationTests.xml"]:
        props = ET.parse(path).find("m:CommonModule/m:Properties", ns)
        if props is None or props.findtext("m:Server", namespaces=ns) != "true":
            raise ValueError(f"Invalid module metadata: {path}")
    manifest = json.loads((ROOT / "docs/baseline/source-manifest.json").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        if not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
            raise ValueError("Invalid baseline hash")
    cases = json.loads((ROOT / "tests/contracts/request-validation.json").read_text(encoding="utf-8"))
    ids = set()
    for case in cases:
        if case["id"] in ids:
            raise ValueError("Duplicate example ID")
        ids.add(case["id"])
        try:
            if not all(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", case[k]) for k in ("start", "end")):
                raise ValueError("format")
            start, end = date.fromisoformat(case["start"]), date.fromisoformat(case["end"])
            valid = start <= end
            if "limitDays" in case:
                valid = valid and (end - start).days + 1 <= case["limitDays"]
            if valid and str(end + timedelta(days=1)) != case["endExclusive"]:
                raise ValueError(f"Wrong exclusive boundary in {case['id']}")
        except (ValueError, OverflowError):
            valid = False
        if valid != case["valid"]:
            raise ValueError(f"Inconsistent date example: {case['id']}")
    print(f"PASS: {len(required)} required artifacts, Markdown links, module XML, source hashes, {len(cases)} contract examples")
    print("NOT RUN: BSL compilation, platform scenarios, University integration, HTTP service")


if __name__ == "__main__":
    main()
