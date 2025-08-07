import argparse
import mimetypes
import sys
import time
import requests

from pathlib import Path


def infer_extension_from_content_type(content_type: str) -> str:
    if not content_type:
        return ".bin"

    content_type = content_type.lower()
    if "jpeg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "mp4" in content_type:
        return ".mp4"

    return ".bin"


def parse_disposition_filename(disposition: str | None) -> str | None:
    if not disposition:
        return None

    # naive parsing: filename="..."
    parts = disposition.split(";")
    for part in parts:
        part = part.strip()
        if part.lower().startswith("filename="):
            value = part.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Клиент для вызова /swap: загрузка изображения и получение результата",
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000/swap", help="URL эндпоинта /swap")
    parser.add_argument("--file", required=True, help="Путь к исходному изображению на ПК")
    parser.add_argument("--template-name", required=True, help="Имя шаблона из папки assets (с расширением)")
    parser.add_argument("--user-uid", required=True, help="Идентификатор пользователя для папки результата")
    parser.add_argument(
        "--out",
        default=None,
        help="Куда сохранить результат (файл). По умолчанию берётся имя из ответа или генерируется автоматически.",
    )
    parser.add_argument("--timeout", type=float, default=120.0, help="Таймаут запроса в секундах")

    args = parser.parse_args()

    source_path = Path(args.file)
    if not source_path.exists():
        print(f"Файл не найден: {source_path}", file=sys.stderr)
        return 1

    mime_type, _ = mimetypes.guess_type(source_path.name)
    if mime_type is None:
        # допустим как octet-stream, сервер проверит content_type по форм-части
        mime_type = "application/octet-stream"

    files = {
        "file": (source_path.name, open(source_path, "rb"), mime_type),
    }
    data = {
        "template_name": args.template_name,
        "user_uid": args.user_uid,
    }

    headers = {"Accept": "image/*"}

    try:
        resp = requests.post(args.url, files=files, data=data, headers=headers, timeout=args.timeout)
    finally:
        # закрыть файловый дескриптор
        try:
            files["file"][1].close()
        except Exception:
            pass

    if resp.status_code >= 400:
        # показать текст ошибки сервера
        preview = resp.text[:1000]
        print(f"Ошибка запроса: HTTP {resp.status_code}: {preview}", file=sys.stderr)
        return 2

    # Определяем имя файла для сохранения
    out_path: Path
    if args.out:
        out_path = Path(args.out)
    else:
        # формируем имя на основе исходника и content-type
        ext = infer_extension_from_content_type(resp.headers.get("Content-Type", ""))
        out_path = Path(f"data/client/result_{source_path.stem}_{int(time.time())}{ext}")

    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(resp.content)

    print(f"OK: сохранено в {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


