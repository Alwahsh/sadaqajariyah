from django import template

from apps.directory.validators import is_known_scheduling_host as _is_known

register = template.Library()


@register.filter
def initials(value):
    if not value:
        return ""
    parts = [p for p in value.split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def is_known_scheduling_host(value):
    return _is_known(value)
