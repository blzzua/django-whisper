import logging
import time
import random
from celery import shared_task
from django.utils import timezone
from .models import MediaFile
import os
import hashlib
import subprocess
import tempfile
import numpy as np
from pydub import AudioSegment, silence
import noisereduce as nr


# --- lazy load whisper model ---
_whisper_model_cache = None
MODEL_NAME = "base"

def get_whisper_model():
    """
    lazy load and cache model Whisper.
    """
    global _whisper_model_cache
    if _whisper_model_cache is None:
        try:
            import whisper
            logging.info(f"Завантаження моделі Whisper: {MODEL_NAME}...")
            _whisper_model_cache = whisper.load_model(MODEL_NAME)
            logging.info("Модель успішно завантажена.")
        except Exception as e:
            logging.error(f"Не вдалося завантажити модель Whisper: {e}")
            _whisper_model_cache = None
            raise RuntimeError(f"Не вдалося завантажити модель Whisper: {e}")
    return _whisper_model_cache

# --- Основна логіка ---
def process_input_file(filepath):
    """
    Обробляє вхідний файл (аудіо або відео).
    Конвертує файл у формат WAV (16kHz, моно, pcm_s16le) за допомогою ffmpeg.
    """
    if not filepath or not os.path.exists(filepath):
        logging.error(f"Файл {filepath} не знайдено.")
        raise FileNotFoundError(f"Файл {filepath} не знайдено.")
    
    try:
        temp_dir = tempfile.mkdtemp(prefix='transcribe_')
        output_wav_path = os.path.join(temp_dir, "processed_audio.wav")
        
        logging.info(f"Конвертація файлу: {filepath} у {output_wav_path}")

        command = [
            "ffmpeg",
            "-i", filepath,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            output_wav_path,
        ]
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        
        logging.info("Конвертація успішно завершена.")
        return output_wav_path, temp_dir

    except subprocess.CalledProcessError as e:
        logging.error(f"Помилка ffmpeg: {e.stderr}")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        raise RuntimeError(f"Помилка обробки файлу за допомогою ffmpeg. Деталі: {e.stderr}")
    except Exception as e:
        logging.error(f"Невідома помилка при обробці файлу: {e}")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        raise RuntimeError(f"Сталася невідома помилка: {e}")

def combine_chunks(audio_chunks, target_length_sec):
    """
    Об'єднує дрібні аудіо-сегменти у більші, заданої довжини.
    """
    target_length_ms = target_length_sec * 1000
    combined_chunks = []
    current_chunk = AudioSegment.silent(duration=0)

    for chunk in audio_chunks:
        if len(current_chunk) + len(chunk) <= target_length_ms:
            current_chunk += chunk
        else:
            if len(current_chunk) > 0:
                combined_chunks.append(current_chunk)
            current_chunk = chunk

    if len(current_chunk) > 0:
        combined_chunks.append(current_chunk)
    
    return combined_chunks

def transcribe_generator(path_to_wav, need_reduce_noise=True, need_split_audio=True, choosed_language="auto"):
    """
    Генератор, який виконує транскрипцію аудіофайлу по частинах.
    - Зменшує шум.
    - Розбиває аудіо на частини по тиші.
    - Транскрибує кожну частину та повертає результат.
    
    Yields:
        str: Частини транскрибованого тексту.
    """
    if not path_to_wav or not os.path.exists(path_to_wav):
        logging.error("Помилка: файл не знайдено.")
        return

    try:
        model = get_whisper_model()
        if model is None:
            logging.error("Модель Whisper не завантажена. Неможливо виконати транскрипцію.")
            return

        sound_file = AudioSegment.from_wav(path_to_wav)
        samples = np.array(sound_file.get_array_of_samples())
        
        if samples.size == 0:
            logging.warning("Аудіофайл порожній.")
            return

        if need_reduce_noise:
            logging.info("Зменшення шуму...")
            reduced_noise_samples = nr.reduce_noise(y=samples, sr=sound_file.frame_rate)
            reduced_audio = AudioSegment(
                reduced_noise_samples.tobytes(),
                frame_rate=sound_file.frame_rate,
                sample_width=sound_file.sample_width,
                channels=sound_file.channels)
            logging.info("Зменшення шуму завершено.")
        else:
            logging.info("Зменшення шуму пропущено")
            reduced_audio = AudioSegment(
                samples.tobytes(),
                frame_rate=sound_file.frame_rate,
                sample_width=sound_file.sample_width,
                channels=sound_file.channels)
        
        if need_split_audio:
            logging.info("Розбиття аудіо на частини...")
            audio_little_chunks = silence.split_on_silence(
                reduced_audio,
                min_silence_len=1250,
                silence_thresh=sound_file.dBFS - 16,
                keep_silence=500
            )
            audio_chunks = combine_chunks(audio_chunks=audio_little_chunks, target_length_sec=60)
            if not audio_chunks:
                logging.warning("Не вдалося розбити аудіо на частини. Спроба транскрибувати цілий файл.")
                audio_chunks = [reduced_audio]
        else:
            logging.warning("Транскрибуємо файл.")
            audio_chunks = [reduced_audio]

        num_chunks = len(audio_chunks)
        logging.info(f"Аудіо розбито на {num_chunks} частин.")

        path_to_wav_dir = os.path.dirname(path_to_wav)

        for i, chunk in enumerate(audio_chunks):
            chunk_filename = os.path.join(path_to_wav_dir, f"chunk_{i:04}.wav")
            chunk.export(chunk_filename, format="wav")
            
            if choosed_language == "auto":
                transcribe_args = {}
            else:
                transcribe_args = {"language": choosed_language}
            
            transcribe_result = model.transcribe(chunk_filename, fp16=False, verbose=False, **transcribe_args)
            
            text = transcribe_result['text'].strip()
            if text:
                yield text + " "
            
            os.remove(chunk_filename)
            logging.info(f"Частина {i+1}/{num_chunks}: {text}")

    except Exception as e:
        logging.error(f"Помилка під час транскрипції: {e}")
        raise



@shared_task
def process_media_file_task(media_file_id):
    try:
        media_file = MediaFile.objects.get(id=media_file_id)
        
        # Оновлюємо статус на "в обробці"
        media_file.status = 'processing'
        media_file.save()
        processed_wav, temp_dir_to_clean = process_input_file(media_file.file.path)
        
        full_transcribed_text = ""
        # Використання генератора для отримання тексту по частинах
        for text_chunk in transcribe_generator(
            path_to_wav=media_file.file.path,
            need_reduce_noise=False,
            need_split_audio=False, # TODO get this field from model
            choosed_language="auto"
        ):
            full_transcribed_text += text_chunk
            media_file.recognized_text = full_transcribed_text
            media_file.save()

        # Оновлюємо результат
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



