from typing import Type

from django import template
from django.core.exceptions import FieldDoesNotExist
from django.db import models

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


@register.simple_tag
def get_field_verbose_name(instance: Type[models.Model], field_name: str):
    """Returns field verbose name.

    Args:
        instance (Type[models.Model]):
        field_name

    Returns:
        str: Field verbose name.
            Empty string if field not found.
    """
    try:
        return instance._meta.get_field(field_name).verbose_name
    except FieldDoesNotExist:
        return ''
