import time
import random
from celery import shared_task
from django.utils import timezone
from .models import MediaFile


@shared_task
def process_media_file_task(media_file_id):
    try:
        media_file = MediaFile.objects.get(id=media_file_id)
        
        # Оновлюємо статус на "в обробці"
        media_file.status = 'processing'
        media_file.save()
        
        # Імітуємо обробку файлу (5-10 секунд)
        processing_time = random.randint(5, 10)
        time.sleep(processing_time)
        
        # Генеруємо mock текст на основі налаштувань
        mock_text = generate_mock_transcription(media_file)
        
        # Оновлюємо результат
        media_file.recognized_text = mock_text
        media_file.status = 'completed'
        
        # Встановлюємо дату видалення файлу (через 30 днів)
        media_file.file_deletion_date = timezone.now() + timezone.timedelta(days=30)
        
        media_file.save()
        
        return f"Обробка файлу {media_file.original_filename} завершена успішно"
        
    except MediaFile.DoesNotExist:
        return f"Файл з ID {media_file_id} не знайдено"
    except Exception as e:
        # У випадку помилки
        try:
            media_file = MediaFile.objects.get(id=media_file_id)
            media_file.status = 'failed'
            media_file.save()
        except:
            pass
        return f"Помилка обробки: {str(e)}"


def generate_mock_transcription(media_file):
    """Генерує mock текст для розпізнавання"""
    
    base_texts = {
        'uk': [
            "Це приклад розпізнаного тексту українською мовою. Система успішно обробила ваш файл.",
            "Вітаємо! Ваш аудіо/відео файл був успішно оброблений нашою системою розпізнавання мови.",
            "Результат автоматичного розпізнавання мовлення. Якість розпізнавання може залежати від якості звуку."
        ],
        'en': [
            "This is an example of recognized text in English. The system has successfully processed your file.",
            "Welcome! Your audio/video file has been successfully processed by our speech recognition system.",
            "Automatic speech recognition result. Recognition quality may depend on audio quality."
        ],
        'ru': [
            "Это пример распознанного текста на русском языке. Система успешно обработала ваш файл.",
            "Добро пожаловать! Ваш аудио/видео файл был успешно обработан нашей системой распознавания речи."
        ]
    }
    
    # Вибираємо базовий текст
    language_texts = base_texts.get(media_file.language, base_texts['uk'])
    base_text = random.choice(language_texts)
    
    # Додаємо інформацію про налаштування
    settings_info = []
    if media_file.noise_cancellation:
        settings_info.append("зменшення шуму: увімкнено")
    if media_file.diarisation:
        settings_info.append("розділення мовців: увімкнено")
    
    if settings_info:
        base_text += f" Налаштування обробки: {', '.join(settings_info)}."
    
    # Додаємо інформацію про файл
    base_text += f" Файл: {media_file.original_filename}"
    base_text += f" Тип: {'відео' if media_file.is_video() else 'аудіо'}"
    
    return base_text
