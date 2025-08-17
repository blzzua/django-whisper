from django import forms
from .models import MediaFile


class MediaFileUploadForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ['file', 'noise_cancellation', 'language', 'diarisation']
        widgets = {
            'file': forms.FileInput(attrs={
                'accept': '.mp3,.wav,.ogg,.aac,.flac,.m4a,.mp4,.avi,.mov,.wmv,.flv,.webm',
                'class': 'form-control',
                'id': 'file-upload'
            }),
            'noise_cancellation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'language': forms.Select(attrs={
                'class': 'form-select'
            }),
            'diarisation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'file': 'Оберіть файл',
            'noise_cancellation': 'Зменшення шуму',
            'language': 'Мова',
            'diarisation': 'Розділення мовців',
        }
    
    language = forms.ChoiceField(
        choices=[
            ('uk', 'Українська'),
            ('en', 'English'),
            ('ru', 'Русский'),
            ('de', 'Deutsch'),
            ('fr', 'Français'),
        ],
        initial='uk',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Перевірка розміру файлу (500 MB)
            if file.size > 524288000:
                raise forms.ValidationError('Розмір файлу не повинен перевищувати 500 МБ.')
            
            # Перевірка типу файлу
            allowed_extensions = ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a', 
                                '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError('Непідтримуваний формат файлу.')
        
        return file
