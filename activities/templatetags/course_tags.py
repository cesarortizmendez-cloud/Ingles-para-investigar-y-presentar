from django import template

register = template.Library()


@register.filter
def get(mapping, key):
    """{{ dict|get:key }} — acceso por clave variable."""
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        try:
            return mapping[key]
        except (KeyError, IndexError, TypeError):
            return None


@register.filter
def pct(value):
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.0f} %"
    except (TypeError, ValueError):
        return "—"


@register.filter
def series_max(series):
    try:
        return max(float(s["value"]) for s in series)
    except (TypeError, ValueError, KeyError):
        return 0


@register.filter
def bar_width(value, maximum):
    try:
        return max(2, round(float(value) / float(maximum) * 100))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0
