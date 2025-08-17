# Register your models here.
from django.contrib import admin
from .models import MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'user', 'file_type', 'status', 
        'upload_date', 'is_shared', 'shared_url'
    ]
    list_filter = ['file_type', 'status', 'is_shared', 'upload_date']
    search_fields = ['original_filename', 'user__username', 'shared_url']
    readonly_fields = ['hash_id', 'upload_date']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('user', 'original_filename', 'file', 'file_type')
        }),
        ('Статус обробки', {
            'fields': ('status', 'recognized_text')
        }),
        ('Налаштування обробки', {
            'fields': ('noise_cancellation', 'language', 'diarisation')
        }),
        ('Спільний доступ', {
            'fields': ('is_shared', 'shared_url')
        }),
        ('Системні поля', {
            'fields': ('hash_id', 'upload_date', 'file_deletion_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')