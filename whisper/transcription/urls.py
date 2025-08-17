from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('my-transcriptions/', views.my_transcriptions_view, name='my_transcriptions'),
    path('transcription/<int:file_id>/', views.transcription_detail_view, name='transcription_detail'),
    path('transcription/<int:file_id>/status/', views.transcription_status_view, name='transcription_status'),
    path('transcription/<int:file_id>/share/', views.toggle_share_view, name='toggle_share'),
    path('shared/<str:shared_url>/', views.shared_transcription_view, name='shared_transcription'),
]
