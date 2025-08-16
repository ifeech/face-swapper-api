from datetime import datetime
from pathlib import Path
from fastapi import UploadFile


def save_uploaded_file(file_data: bytes, filename: str) -> Path:
    """
    Сохраняет файл в папку input с уникальным именем в подпапке месяц_год
    
    Args:
        file_data: Данные файла в байтах
        original_filename: Оригинальное имя файла
    
    Returns:
        Path: Путь к сохранённому файлу
    """
    now = datetime.now()
    month_year = now.strftime("%m_%Y")
    
    # Создаём путь к директории
    input_dir = Path("data/input") / month_year
    input_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = input_dir / filename
    
    with open(file_path, "wb") as f:
        f.write(file_data)
    
    return file_path


def get_file_info(file_path: Path) -> dict:
    """
    Получает информацию о сохранённом файле
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        dict: Информация о файле
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    stat = file_path.stat()
    return {
        "path": str(file_path),
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "name": file_path.name,
        "extension": file_path.suffix
    }

async def save_upload_stream(upload: UploadFile, filename: str, user_uid: str, max_mb: int = 10) -> Path:
    """
    Потоково сохраняет загруженный файл, ограничивая максимальный размер.

    Args:
        upload: UploadFile из FastAPI
        filename: имя файла для сохранения
        user_uid: id пользователя для создания уникальной подпапки
        max_mb: лимит размера в мегабайтах

    Returns:
        Path к сохранённому файлу

    Raises:
        ValueError: при превышении лимита размера
    """
    now = datetime.now()
    month_year = now.strftime("%m_%Y")
    input_dir = Path("data/input") / user_uid / month_year
    input_dir.mkdir(parents=True, exist_ok=True)

    dst_path = input_dir / filename

    limit_bytes = max_mb * 1024 * 1024
    written = 0
    chunk_size = 1024 * 1024  # 1MB

    with dst_path.open("wb") as dst:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            written += len(chunk)
            if written > limit_bytes:
                dst.close()
                try:
                    dst_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise ValueError(f"Превышен лимит размера файла: > {max_mb} МБ")
            dst.write(chunk)

    return dst_path
