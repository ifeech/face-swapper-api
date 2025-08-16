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

`data/input/` - папка с переданными изображениями

## Способы запуска клиента (получение результата как файла)

**Встроенный скрипт-клиент:**
- Требуется пакет `requests`.
- Запуск через uv:
```bash
uv run python scripts/facefusion_client.py --host http://127.0.0.1:8000 --source-file source.jpg --template-file template.jpg --user-uid 123 --out result.jpg
```

**Либо установите requests вручную и запустите обычным Python:**
```bash
pip install requests
python scripts/facefusion_client.py --host http://127.0.0.1:8000 \
  --source-file source.jpg \
  --template-file template.jpg \
  --user-uid 123
```

**curl** 

(см. ниже раздел «Эндпоинт API»)

## Эндпоинт API

- Метод: `POST /facefusion`
- Тип: `multipart/form-data`
- Поля формы:
  - `source`: файл с исходным изображением, где нужно заменить лицо (`image/jpeg` или `image/png`)
  - `template`: файл шаблона — изображение или видео (`image/jpeg`, `image/png`, или `video/mp4`). Видео-шаблоны поддерживаются.
  - `user_uid`: идентификатор пользователя; результат сохраняется в `data/output/<user_uid>/...`

Ответ: файл (изображение или видео) с соответствующим Content-Type (`image/jpeg`, `image/png` или `video/mp4`) — готовый к отправке во внешний сервис.

### Примеры вызова

curl (пример с изображением в качестве шаблона):

```bash
curl -X POST "http://127.0.0.1:8000/facefusion" \
  -H "Accept: image/*" \
  -F "source=@/path/to/source.jpg;type=image/jpeg" \
  -F "template=@/path/to/template.jpg;type=image/jpeg" \
  -F "user_uid=123e4567" \
  --output result.jpg
```

curl (пример с видео-шаблоном):

```bash
curl -X POST "http://127.0.0.1:8000/facefusion" \
  -H "Accept: video/mp4" \
  -F "source=@/path/to/source.jpg;type=image/jpeg" \
  -F "template=@/path/to/template.mp4;type=video/mp4" \
  -F "user_uid=123e4567" \
  --output result.mp4
```

## Замечания

- Первый запуск может скачивать модели FaceFusion (папка `data/models/`).
- Если `facefusion` не найден, сервер вернёт 500 с подсказкой установить CLI.
- Ограничение размера загрузки по умолчанию ~10 МБ.
