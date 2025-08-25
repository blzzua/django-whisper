# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import MediaFile
from .forms import MediaFileUploadForm
from .tasks import process_media_file_task
import logging

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Реєстрація пройшла успішно!')
            return redirect('upload')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def upload_view(request):
    if request.method == 'POST':
        form = MediaFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            media_file = form.save(commit=False)
            media_file.user = request.user
            media_file.original_filename = request.FILES['file'].name
            
            # Визначаємо тип файлу
            if media_file.is_video():
                media_file.file_type = 'video'
            elif media_file.is_audio():
                media_file.file_type = 'audio'
            
            media_file.save()
            
            # Запускаємо фонову обробку
            logging.info('process_media_file_task.delay(media_file.id)')
            process_media_file_task.delay(media_file.id)
            logging.info('Файл завантажено і відправлено на обробку!')

            messages.success(request, 'Файл завантажено і відправлено на обробку!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'message': 'Файл завантажено успішно!',
                    'redirect': '/my-transcriptions/'
                })
            
            return redirect('my_transcriptions')
    else:
        form = MediaFileUploadForm()
    
    return render(request, 'transcription/upload.html', {'form': form})


@login_required
def my_transcriptions_view(request):
    media_files = MediaFile.objects.filter(user=request.user)
    
    if request.headers.get('HX-Request'):
        return render(request, 'transcription/partials/transcription_table.html', {
            'media_files': media_files
        })
    
    return render(request, 'transcription/my_transcriptions.html', {
        'media_files': media_files
    })


@login_required
@require_http_methods(["GET"])
def transcription_status_view(request, file_id):
    media_file = get_object_or_404(MediaFile, id=file_id, user=request.user)
    
    return JsonResponse({
        'status': media_file.status,
        'status_display': media_file.get_status_display(),
    })


@login_required
def transcription_detail_view(request, file_id):
    media_file = get_object_or_404(MediaFile, id=file_id, user=request.user)
    
    if request.headers.get('HX-Request'):
        return render(request, 'transcription/partials/transcription_detail.html', {
            'media_file': media_file
        })
    
    return render(request, 'transcription/transcription_detail.html', {
        'media_file': media_file
    })


@login_required
@require_http_methods(["POST"])
def toggle_share_view(request, file_id):
    media_file = get_object_or_404(MediaFile, id=file_id, user=request.user)
    media_file.is_shared = not media_file.is_shared
    media_file.save()
    
    return JsonResponse({
        'is_shared': media_file.is_shared,
        'shared_url': media_file.shared_url if media_file.is_shared else None
    })


def shared_transcription_view(request, shared_url):
    media_file = get_object_or_404(MediaFile, shared_url=shared_url, is_shared=True)
    
    return render(request, 'transcription/shared_transcription.html', {
        'media_file': media_file
    })
