from django import template

from core import settings


AVAILABLE_SETTINGS = [
    'PROJECT_BUILD_HASH',
    'PROJECT_TITLE',
    'PROJECT_DESCRIPTION',
    'PROJECT_URL',
    'PROJECT_KEYWORDS',
    'PROJECT_ROBOTS'
]


register = template.Library()


@register.simple_tag
def get_setting(value: str):
    setting_name: str = value.upper()

    if setting_name not in AVAILABLE_SETTINGS:
        raise RuntimeError('Setting %s is not available' % value)

    try:
        return settings.__getattribute__(setting_name)
    except AttributeError:
        raise RuntimeError('Setting %s is not found' % setting_name)
