from django.contrib import admin
from django.contrib.admin.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'action_time'

    list_filter = (
        'user',
        'content_type',
        'action_flag',
    )

    search_fields = (
        'object_repr',
        'change_message',
    )

    list_display = (
        'action_time',
        'user',
        'content_type',
        'action_flag',
    )
