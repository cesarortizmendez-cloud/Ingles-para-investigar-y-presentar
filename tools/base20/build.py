"""Genera content/base20.json y content/days/B01.json … B20.json (plan base de 20 días).

Uso:  python tools/base20/build.py

Reutiliza los bloques del plan de 40 días (tools/plan40/build.py) con días más cortos (≈75 min) y
registro cotidiano. Los datos editoriales están en unit1.py … unit4.py (mismo formato que plan40).
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "plan40"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("plan40_build", HERE.parent / "plan40" / "build.py")
b40 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b40)  # bloques comunes del plan de 40 días
sys.path[:] = [p for p in sys.path if p != str(HERE.parent / "plan40")]
sys.modules.pop("meta", None)  # el meta.py de plan40 no debe tapar el de base20
sys.path.insert(0, str(HERE))

from learning_core import contract  # noqa: E402

import meta  # noqa: E402

PREFIX = "B"
VERSION = "1.0.0"
b40.MINUTES = {"vocabulario": 15, "gramatica": 15, "escucha": 10, "lectura": 10, "habla": 10, "escritura": 5}
b40.REGISTER = "cotidiano"
b40.QUALITY = {"authors": ["Claude (redacción inicial)"], "reviewed_by": "", "license": "Original del proyecto",
               "date": "2026-11-08", "changelog": [{"version": VERSION, "date": "2026-11-08",
                                                   "change": "Plan base de 20 días, versión inicial."}]}

UNITS = [importlib.import_module(f"unit{i}").DAYS for i in range(1, 5)]


def main():
    out = ROOT / "content" / "days"
    out.mkdir(parents=True, exist_ok=True)
    all_days, errors, learning_so_far = [], [], []
    for udays in UNITS:
        learning = [d for d in udays if not d.get("review") and not d.get("final")]
        for d in udays:
            if d.get("final"):
                pkg = b40.build_review_day(d, (learning_so_far + learning)[-10:], final=True, prefix=PREFIX)
            elif d.get("review"):
                pkg = b40.build_review_day(d, learning, prefix=PREFIX)
            else:
                pkg = b40.build_learning_day(d, prefix=PREFIX)
            errors += contract.validate(pkg)
            (out / f"{pkg['id']}.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=1), encoding="utf-8")
            all_days.append({"day": d["n"], "code": pkg["id"], "week": d["week"], "title": d["title"], "type": pkg["day_type"]})
        learning_so_far += learning
    plan = dict(meta.PLAN)
    plan["days"] = sorted(all_days, key=lambda x: x["day"])
    if [d["day"] for d in plan["days"]] != list(range(1, 21)):
        errors.append("El plan base debe tener exactamente los días 1…20")
    (ROOT / "content" / "base20.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    words = sum(len(d["vocab"]) for u in UNITS for d in u if "vocab" in d)
    print(f"{len(all_days)} días generados · {words} unidades léxicas")
    if errors:
        print("\n".join(errors))
        sys.exit(1)


if __name__ == "__main__":
    main()
