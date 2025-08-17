import os
import hashlib
import base62
from django.conf import settings
from django.utils import timezone


def generate_hash_id(filename):
    """Генерує унікальний hash_id для файлу"""
    hash_source = f"{filename}{timezone.now()}"
    return hashlib.md5(hash_source.encode()).hexdigest()


def generate_shared_url(hash_id):
    """Генерує короткий Base62 URL для спільного доступу"""
    hash_int = int(hash_id[:8], 16)
    return base62.encode(hash_int)[:8]


def get_file_type(filename):
    """Визначає тип файлу на основі розширення"""
    extension = os.path.splitext(filename)[1].lower()
    
    video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
    audio_extensions = ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a']
    
    if extension in video_extensions:
        return 'video'
    elif extension in audio_extensions:
        return 'audio'
    else:
        return None


def is_allowed_file_type(filename):
    """Перевіряє чи дозволений тип файлу"""
    return get_file_type(filename) is not None


def format_file_size(size_bytes):
    """Форматує розмір файлу в людський вигляд"""
    if size_bytes == 0:
        return "0 Б"
    
    size_names = ["Б", "КБ", "МБ", "ГБ"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def md5_to_base62(file_path, num_bits=34):
    """
    Обчислює MD5-хеш файлу, бере перші `num_bits` біт і кодує їх у формат Base62.
    Args:
        file_path (str): Шлях до файлу.
        num_bits (int): Кількість біт хешу, яку потрібно використовувати.
    Returns:
        str: Рядок у форматі Base62.
    """

    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    BASE = len(ALPHABET)
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                md5_hash.update(chunk)
    except FileNotFoundError:
        return None
    md5_integer = int(md5_hash.hexdigest(), 16)

    mask = (1 << num_bits) - 1
    shortened_hash = md5_integer & mask
    base62_string = ""
    if shortened_hash == 0:
        return ALPHABET[0]
    while shortened_hash > 0:
        remainder = shortened_hash % BASE
        base62_string = ALPHABET[remainder] + base62_string
        shortened_hash //= BASE
    return base62_string
