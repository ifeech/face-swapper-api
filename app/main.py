import os
import uuid
import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv

from app.services.facefusion import FacefusionService
from app.utils.file_manager import save_upload_stream


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("face_swapper")

# Загружаем переменные окружения из .env (если файл есть в корне проекта)
load_dotenv()


app = FastAPI()


@app.post("/facefusion")
async def swap(
    source: UploadFile = File(...),
    template: UploadFile = File(...),
    user_uid: str = Form(...),
    content_length: int | None = Header(default=None, alias="Content-Length"),
):
    # Проверка типа контента
    if source.content_type not in {"image/jpeg", "image/png"}:
        logger.warning(
            "Unsupported content type: %s for filename=%s user_uid=%s",
            source.content_type,
            source.filename,
            user_uid,
        )
        raise HTTPException(415, "Unsupported format")

    if template.content_type not in {"image/jpeg", "image/png", "video/mp4"}:
        logger.warning(
            "Unsupported content type: %s for template=%s user_uid=%s",
            template.content_type,
            template.filename,
            user_uid,
        )
        raise HTTPException(415, "Unsupported format")

    max_source_size_mb = int(os.getenv("MAX_SOURCE_FILE_SIZE_MB"))
    max_template_size_mb = int(os.getenv("MAX_TEMPLATE_SIZE_MB"))

    max_content_length_mb = max_source_size_mb+max_template_size_mb
    # Проверка размера до чтения (если сервер/клиент передал Content-Length)
    if content_length is not None and content_length > max_content_length_mb * 1024 * 1024:
        raise HTTPException(413, f"Переданные файлы слишком большие. Лимит: {max_content_length_mb} МБ")
    
    # Потоковое сохранение с жёстким лимитом размера

    u_name = uuid.uuid4().hex[:8]

    source_extension = source.content_type.split('/')[1]
    source_name = f"source_{u_name}.{source_extension}"
    try:
        saved_source_path = await save_upload_stream(source, source_name, user_uid, max_mb=max_source_size_mb)
    except ValueError as e:
        logger.warning("Upload size exceeded for user_uid=%s filename=%s: %s", user_uid, source.filename, e)
        raise HTTPException(413, str(e))
    
    template_extension = template.content_type.split('/')[1]
    template_name = f"template_{u_name}.{template_extension}"
    try:
        saved_template_path = await save_upload_stream(template, template_name, user_uid, max_mb=max_template_size_mb)
    except ValueError as e:
        logger.warning("Upload size exceeded for user_uid=%s filename=%s: %s", user_uid, template.filename, e)
        raise HTTPException(413, str(e))
    
    fusion_service = FacefusionService()

    # Обрабатываем файл
    try:
        output_name = f"result_{u_name}.{template_extension}"
        result = fusion_service.swap_faces(
            source_image_path=str(saved_source_path),
            template_image_path=str(saved_template_path),
            output_name=output_name,
            user_uid=user_uid,
        )
    except FileNotFoundError as e:
        logger.warning("Template/source not found for user_uid=%s: %s", user_uid, e)
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        logger.exception("FaceFusion error for user_uid=%s: %s", user_uid, e)
        raise HTTPException(500, str(e))

    output_path = result["output_path"]
    suffix = Path(output_path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix == ".mp4":
        media_type = "video/mp4"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=output_path, media_type=media_type, filename=Path(output_path).name)
