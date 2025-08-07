# Face Swapper (FastAPI + FaceFusion 3)

Сервис для замены лиц на изображениях. Принимает фото-источник и имя шаблона из папки `data/assets`, запускает FaceFusion 3, возвращает результат как файл-изображение.

## Требования
- Python 3.12+
- Windows / Linux / macOS
- Установленный FaceFusion 3 (по инструкции из репозитория) и доступ к CLI (`facefusion`), либо к `python facefusion.py run` в окружении conda

## Установка зависимостей сервиса

Через uv (рекомендуется):
```bash
uv sync
```

Или через pip:
```bash
pip install -e .
```

## Установка FaceFusion 3

Смотрите официальную документацию и README: [FaceFusion на GitHub](https://github.com/facefusion/facefusion?tab=readme-ov-file)

Интеграция с нашим сервисом (варианты):
- Вариант A: добавьте `facefusion` в PATH (если у вас есть системный исполняемый CLI). Тогда сервис просто вызовет `facefusion headless-run ...`.
- Вариант B (рекомендуется для conda): заполните `.env` в корне проекта — сервис сам прочитает переменные

  Пример файла `.env`:
  ```env
  # Путь к скаченному репозиторию FaceFusion, где лежит facefusion.py
  FACEFUSION_HOME=
  # Имя conda-окружения (указав будет запуск через conda)
  # Если указано - игнорируется FACEFUSION_PYTHON
  FACEFUSION_CONDA_ENV=
  # Явный путь к интерпретатору Python для запуска facefusion (указать, если не запускать через conda)
  # Это может быть путь до интерпритатора из окружения (например, \envs\facefusion\python.exe)
  FACEFUSION_PYTHON=
  
  # Необязательно: директория для моделей/кэша (по умолчанию data/models)
  FACEFUSION_MODELS_DIR=
  ```

  Сервис при запуске читает `.env` автоматически и формирует команду запуска:
  - `conda run -n <FACEFUSION_CONDA_ENV> python facefusion.py headless-run ...` если указаны `FACEFUSION_HOME` и `FACEFUSION_CONDA_ENV`;
  - `<FACEFUSION_PYTHON> facefusion.py headless-run ...` если указан `FACEFUSION_HOME` и `FACEFUSION_PYTHON`;
  - либо просто `facefusion headless-run ...`, если переменные не заданы (CLI должен быть доступен в PATH).

## Запуск сервера

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

По умолчанию результаты замены лица сохраняются в папку `data/output/`.

- `data/assets/` - папка с изображениями-шаблонами
- `data/input/` - папка с переданными фотографиями 

## Способы запуска клиента (получение результата как файла)

**Встроенный скрипт-клиент:**
- Требуется пакет `requests`.
- Запуск через uv:
```bash
uv run python scripts/swap_client.py --url http://127.0.0.1:8000/swap --file ./tests/data/source.jpg --template-name template.jpg --user-uid 123e4567 --out result.jpg
```

**Либо установите requests вручную и запустите обычным Python:**
```bash
pip install requests
python scripts/swap_client.py --url http://127.0.0.1:8000/swap \
  --file ./tests/data/source.jpg \
  --template-name template.jpg \
  --user-uid 123e4567
```

**curl** 

(см. ниже раздел «Эндпоинт API»)

## Эндпоинт API

- Метод: `POST /swap`
- Тип: `multipart/form-data`
- Поля формы:
  - `file`: изображение с лицом (`image/jpeg` или `image/png`)
  - `template_name`: имя файла шаблона из папки `data/assets/` (например, `celebrity.jpg`)
  - `user_uid`: идентификатор пользователя; результат сохраняется в `output/<user_uid>/...`

Ответ: файл-изображение (контент `image/jpeg` или `image/png`), готовый к отправке во внешний сервис (например, Telegram).

### Примеры вызова

curl:
```bash
curl -X POST "http://127.0.0.1:8000/swap" \
  -H "Accept: image/jpeg" \
  -F "file=@/path/to/source.jpg;type=image/jpeg" \
  -F "template_name=template.jpg" \
  -F "user_uid=123e4567" \
  --output result.jpg
```

Python (requests):
```python
import requests

url = "http://127.0.0.1:8000/swap"
with open("/path/to/source.jpg", "rb") as f:
    files = {"file": ("source.jpg", f, "image/jpeg")}
    data = {"template_name": "template.jpg", "user_uid": "123e4567"}
    r = requests.post(url, files=files, data=data)
    r.raise_for_status()
    with open("result.jpg", "wb") as out:
        out.write(r.content)
```

## Замечания
- Первый запуск может скачивать модели FaceFusion (папка `data/models/`).
- Если `facefusion` не найден, сервер вернёт 500 с подсказкой установить CLI.
- Ограничение размера загрузки по умолчанию ~10 МБ.
