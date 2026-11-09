from django.urls import reverse
from django.utils import timezone

from activities.models import Attempt
from curriculum.models import ContentPackage
from learning_core import contract, grading, plan, programs
from review.models import ReviewItem


BLOCK_LABELS = {
    "vocabulario": ("Vocabulario", "🔤"),
    "gramatica": ("Gramática", "🧩"),
    "escucha": ("Escucha", "🎧"),
    "lectura": ("Lectura", "📄"),
    "habla": ("Habla", "🎙️"),
    "escritura": ("Escritura", "✍️"),
}


# Capítulos complementarios de la ruta larga y la semana del plan que refuerzan.
CHAPTER_WEEK = {"C01": 1, "C11": 4}


def day_code(n: int, slug: str = "plan40") -> str:
    return programs.day_code(slug, n)


def is_day_code(code: str) -> bool:
    """True para días de cualquier programa (B01…B20, D01…D40)."""
    return programs.for_code(code) is not None


def day_url(slug: str, n: int) -> str:
    return reverse("plan_day", args=[n]) if slug == "plan40" else reverse("program_day", args=[slug, n])


def calendar_url(slug: str) -> str:
    return reverse("plan_calendar") if slug == "plan40" else reverse("program_calendar", args=[slug])


def day_titles() -> dict[str, str]:
    """{"D05": "Día 5 · Números…", "B03": "Base 20 · Día 3 · …"} para todos los programas con contenido."""
    from curriculum.services import load_program
    out = {}
    for prog in programs.PROGRAMS:
        try:
            days = load_program(prog["slug"])["days"]
        except FileNotFoundError:
            continue
        label = "" if prog["slug"] == programs.MAIN else f"{prog['short']} · "
        out.update({d["code"]: f"{label}Día {d['day']} · {d['title']}" for d in days})
    return out


def _activity_index(data: dict) -> dict[str, dict]:
    return {a["id"]: a for _l, a in contract.iter_activities(data)}


def progress_for(user, packages: dict[str, ContentPackage], slug: str = "plan40") -> dict[int, dict]:
    """Progreso de cada día de un programa con contenido importado, usando una sola consulta de intentos."""
    prefix = programs.get(slug)["prefix"]
    attempts = (Attempt.objects.filter(user=user, chapter_code__startswith=prefix)
                .order_by("created_at").values("chapter_code", "activity_id", "status", "score", "activity_type"))
    by_day: dict[str, list] = {}
    for a in attempts:
        by_day.setdefault(a["chapter_code"], []).append(a)
    out = {}
    for code, pkg in packages.items():
        if pkg.kind != "day" or not code.startswith(prefix):
            continue
        acts = _activity_index(pkg.data)
        seen, first_closed = set(), []
        for a in by_day.get(code, []):
            if a["activity_id"] not in acts or a["activity_id"] in seen:
                continue
            seen.add(a["activity_id"])
            if a["activity_type"] in grading.CLOSED_TYPES and a["status"] == grading.GRADED and a["score"] is not None:
                first_closed.append(a["score"])
        prog = plan.day_progress(len(acts), len(seen), first_closed)
        blocks = []
        for lsn in pkg.data["lessons"]:
            ids = [a["id"] for a in lsn["activities"]]
            label, icon = BLOCK_LABELS.get(lsn["kind"], (lsn["kind"], "•"))
            blocks.append({"kind": lsn["kind"], "label": label, "icon": icon, "minutes": lsn.get("minutes", 0),
                           "done": sum(1 for i in ids if i in seen), "total": len(ids), "lesson_id": lsn["id"]})
        prog["blocks"] = blocks
        out[pkg.data["day"]] = prog
    return out


def block_progress(user, pkg: ContentPackage) -> dict[str, dict]:
    done_ids = set(Attempt.objects.filter(user=user, chapter_code=pkg.code).values_list("activity_id", flat=True))
    out = {}
    for lsn in pkg.data["lessons"]:
        ids = [a["id"] for a in lsn["activities"]]
        out[lsn["id"]] = {"done": len([i for i in ids if i in done_ids]), "total": len(ids)}
    return out


def stats(user, slug: str = "plan40") -> dict:
    """Racha (toda práctica cuenta) y palabras en repaso de un programa."""
    prefix = programs.get(slug)["prefix"]
    today = timezone.localdate()
    dates = {timezone.localtime(d).date() for d in
             Attempt.objects.filter(user=user).values_list("created_at", flat=True)}
    words_seen = ReviewItem.objects.filter(user=user, kind="lexis", chapter_code__startswith=prefix).count()
    words_retained = ReviewItem.objects.filter(user=user, kind="lexis", chapter_code__startswith=prefix, stage__gte=2).count()
    return {"streak": plan.streak(dates, today), "words_seen": words_seen, "words_retained": words_retained,
            "practice_days": len(dates)}


def display_name(user, profile) -> str:
    return (profile.display_name or user.first_name or user.get_username()).split(" ")[0]


def phrase_of_day(data: dict) -> tuple[str, str]:
    lex = data.get("language_focus", {}).get("lexis", [])
    if lex:
        return lex[0]["example"], lex[0]["example_es"]
    for r in data.get("resources", []):
        if r.get("type") == "text":
            en = r["body"].split(". ")[0].rstrip(".") + "."
            es = (r.get("translation_es") or "").split(". ")[0].rstrip(".") + "."
            return en, es
    return "", ""


def program_overview(user, profile, packages=None) -> list[dict]:
    """Resumen de cada programa para inicio, ruta, repaso y diagnóstico: iniciado, día de hoy, avance."""
    from curriculum.services import current_packages, load_program
    packages = packages if packages is not None else current_packages()
    today = timezone.localdate()
    out = []
    for prog in programs.PROGRAMS:
        try:
            meta = load_program(prog["slug"])
        except FileNotFoundError:
            continue
        start = profile.program_start(prog["slug"])
        progress = progress_for(user, packages, prog["slug"])
        done = sum(1 for p in progress.values() if p.get("done"))
        today_n = plan.recommended_day(start, today, prog["total"]) if start else None
        title = next((d["title"] for d in meta["days"] if d["day"] == today_n), "") if today_n else ""
        out.append({**prog, "meta": meta, "start": start, "started": start is not None, "done": done,
                    "finished": done >= prog["total"], "today_n": today_n, "today_title": title,
                    "pct": round(done * 100 / prog["total"]),
                    "today_url": day_url(prog["slug"], today_n) if today_n else None,
                    "calendar_url": calendar_url(prog["slug"])})
    return out


def focus_program(overview: list[dict]) -> dict | None:
    """El programa al que apuntan los botones «seguir»: el plan de 40 si está iniciado; si no, la base."""
    started = [p for p in overview if p["started"]]
    main = next((p for p in started if p["slug"] == programs.MAIN), None)
    base = next((p for p in started if p["slug"] != programs.MAIN and not p["finished"]), None)
    return main or base or (started[0] if started else None)
