# Create your models here.
import os
import hashlib
import base64
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MediaFile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В очікуванні'),
        ('processing', 'В обробці'),
        ('completed', 'Готово'),
        ('failed', 'Помилка'),
    ]
    
    FILE_TYPE_CHOICES = [
        ('video', 'Відео'),
        ('audio', 'Аудіо'),
    ]
    
    hash_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='uploads/%Y-%m/')
    original_filename = models.CharField(max_length=255)
    original_filesize = models.IntegerField(null=True, default=None)
    upload_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    recognized_text = models.TextField(null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    need_split_audio = models.BooleanField(default=False,null=False)
    is_shared = models.BooleanField(default=False)
    is_example = models.BooleanField(default=False)
    shared_url = models.CharField(max_length=10, unique=True, null=True, blank=True)
    
    # Додаткові опції обробки
    noise_cancellation = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='uk')
    diarisation = models.BooleanField(default=False)
    
    # Для автоматичного видалення файлів
    file_deletion_date = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.hash_id and self.file:
            # Генеруємо hash_id на основі імені файлу та часу
            hash_source = f"{self.original_filename}{timezone.now()}"
            self.hash_id = hashlib.md5(hash_source.encode()).hexdigest()
        
        if self.is_shared and not self.shared_url:
            # Генеруємо короткий Base62 URL
            hash_int = int(self.hash_id[:8], 16)
            self.shared_url = self.hash_id
        if self.original_filesize is None:
            original_filesize = self.file.size

        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()
    
    def is_video(self):
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        return self.get_file_extension() in video_extensions
    
    def is_audio(self):
        audio_extensions = ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a']
        return self.get_file_extension() in audio_extensions
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Медіафайл'
        verbose_name_plural = 'Медіафайли'
    
    def __str__(self):
        return f"{self.original_filename} - {self.user.username}"
