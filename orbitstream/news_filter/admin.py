from django.contrib import admin
from .models import FilterPreset


@admin.register(FilterPreset)
class FilterPresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'source', 'sort_by', 'created_at']
    list_filter = ['source', 'sort_by', 'created_at']
    search_fields = ['name', 'user__username', 'search_query']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name')
        }),
        ('Filter Settings', {
            'fields': ('search_query', 'date_from', 'date_to', 'sort_by', 'source')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
