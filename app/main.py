import uuid

import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.services.fusion import FusionService
from app.utils.file_manager import save_upload_stream
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("face_swapper")

app = FastAPI()

@app.post("/swap")
async def swap(
    file: UploadFile = File(...),
    template_name: str = Form(...),
    user_uid: str = Form(...),
    content_length: int | None = Header(default=None, alias="Content-Length"),
):
    # Проверка типа контента
    if file.content_type not in {"image/jpeg", "image/png"}:
        logger.warning(
            "Unsupported content type: %s for filename=%s user_uid=%s",
            file.content_type,
            file.filename,
            user_uid,
        )
        raise HTTPException(415, "Unsupported format")

    MAX_FILE_SIZE_MB = 10

    # Проверка размера до чтения (если сервер/клиент передал Content-Length)
    if content_length is not None and content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Файл слишком большой. Лимит: {MAX_FILE_SIZE_MB} МБ")
    
    extension = ".jpg" if file.content_type == "image/jpeg" else ".png"
    filename = f"upload_{uuid.uuid4().hex[:8]}{extension}"

    # Потоковое сохранение с жёстким лимитом размера
    try:
        saved_file_path = await save_upload_stream(file, filename, max_mb=MAX_FILE_SIZE_MB)
    except ValueError as e:
        logger.warning("Upload size exceeded for user_uid=%s filename=%s: %s", user_uid, file.filename, e)
        raise HTTPException(413, str(e))
    
    fusion_service = FusionService()

    # Обрабатываем файл
    try:
        result = fusion_service.swap_faces(
            source_image_path=str(saved_file_path),
            template_name=template_name,
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
