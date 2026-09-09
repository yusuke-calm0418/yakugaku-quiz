from django.contrib import admin
from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'updated_at')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'body')
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at', 'updated_at')
    fields = ('title', 'body', 'is_published', 'published_at', 'created_at', 'updated_at')
