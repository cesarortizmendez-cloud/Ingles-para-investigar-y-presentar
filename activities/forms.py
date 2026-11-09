"""Convierte el POST de una actividad en el formato de respuesta de learning_core.grading."""

ALLOWED_HELPS = {"transcript", "slow_audio", "translation", "hint", "glossary", "model_audio"}


def parse_response(activity: dict, post) -> dict:
    kind = activity["type"]
    if kind == "choice":
        return {"option": post.get("option", ""), "justification": post.get("justification", ""),
                "evidence": post.getlist("evidence")}
    if kind == "cloze":
        return {"gaps": {k: post.get(f"gap_{k}", "") for k in activity["gaps"]}}
    if kind == "ordering":
        ids = [i["id"] for i in activity["items"]]
        positions = {}
        for i in ids:
            try:
                positions[i] = int(post.get(f"pos_{i}", ""))
            except ValueError:
                return {"order": [], "justification": post.get("justification", "")}
        if sorted(positions.values()) != list(range(1, len(ids) + 1)):
            return {"order": [], "justification": post.get("justification", "")}
        return {"order": sorted(ids, key=lambda i: positions[i]), "justification": post.get("justification", "")}
    if kind == "numeric":
        return {"fields": {f["id"]: post.get(f"num_{f['id']}", "") for f in activity["fields"]}}
    if kind in ("short_text", "dictation", "open_text"):
        return {"text": post.get("text", "")[:5000]}
    if kind == "listening":
        out = {}
        for q in activity["questions"]:
            if "options" in q:
                out[q["id"]] = {"option": post.get(f"q_{q['id']}", "")}
            else:
                out[q["id"]] = {"fields": {f["id"]: post.get(f"q_{q['id']}_{f['id']}", "") for f in q["fields"]}}
        return {"questions": out}
    if kind == "oral":
        try:
            rec = int(post.get("recording_id") or 0) or None
        except ValueError:
            rec = None
        return {"recording_id": rec, "transcript": post.get("transcript", "")[:5000],
                "no_mic": post.get("no_mic") == "1"}
    return {}


def parse_helps(post) -> list[str]:
    raw = set(post.getlist("helps"))
    for item in post.get("helps_csv", "").split(","):
        if item.strip():
            raw.add(item.strip())
    return sorted(raw & ALLOWED_HELPS)


def parse_duration(post) -> int | None:
    try:
        value = int(post.get("elapsed_ms") or 0)
    except ValueError:
        return None
    return value if 0 < value < 6 * 3600 * 1000 else None
