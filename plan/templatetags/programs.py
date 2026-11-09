"""Enlaces a días y calendarios de cualquier programa: {% day_url "base20" 3 %}, {% day_link pkg_code %}."""
from django import template

from learning_core import programs
from plan import services

register = template.Library()


@register.simple_tag
def day_url(slug, n):
    return services.day_url(slug, int(n))


@register.simple_tag
def calendar_url(slug):
    return services.calendar_url(slug)


@register.filter
def program_slug(code):
    prog = programs.for_code(code or "")
    return prog["slug"] if prog else ""


@register.filter
def program_short(code):
    prog = programs.for_code(code or "")
    return prog["short"] if prog else ""
