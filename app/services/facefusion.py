"""
Service for face fusion and swapping operations
"""

import os
import subprocess
import logging

from datetime import datetime
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv


class FacefusionService:
    """Сервис для обработки и слияния лиц на базе FaceFusion 3"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("face_swapper.fusion")
        self.output_dir = Path("data/output")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.models_dir = Path("data/models") # для facefusion кэш/модели
        self.models_dir.mkdir(exist_ok=True, parents=True)

    def swap_faces(
        self, 
        source_image_path: str, 
        template_image_path: str,
        output_name: str,
        user_uid: str,
    ) -> Dict[str, str]:
        """
        Запускает замену лица: перенос лица с source на template.

        Returns:
            dict с путями к файлам
        """

        source = self._build_path(source_image_path)
        template = self._build_path(template_image_path)
        output = self._build_output_path(output_name, user_uid)

        self._run_facefusion(source=source, template=template, output=output)
        
        return {
            "source_path": str(source.resolve()),
            "template_path": str(template.resolve()),
            "output_path": str(output.resolve()),
            "user_uid": user_uid,
        }

    def _build_path(self, source_image_path: str) -> Path:
        source = Path(source_image_path)
        if not source.exists():
            self.logger.warning("Source not found: %s", source)
            raise FileNotFoundError(f"Исходное изображение не найдено: {source}")
        
        return source.resolve()

    def _build_output_path(self, output_name: str, user_uid: str) -> Path:
        now = datetime.now()
        month_year = now.strftime("%m_%Y")
        user_dir = self.output_dir / user_uid / month_year
        user_dir.mkdir(parents=True, exist_ok=True)
        
        return (user_dir / output_name).resolve()

    def _run_facefusion(self, source: Path, template: Path, output: Path) -> None:
        """Запуск facefusion 3 через CLI.

        Используем режим face swap: target = шаблон, face = источник.
        Пример команды (минимальная):
        facefusion run --target <template> --face <source> --output <output>
        """
        # Загружаем переменные окружения из .env (если файл есть в корне проекта)
        load_dotenv()

        env = os.environ.copy()
        env.setdefault("FACEFUSION_ROOT", str(Path.cwd()))
        env.setdefault("FACEFUSION_MODELS_DIR", str(self.models_dir))

        # Формируем команду запуска с учётом возможной установки через conda
        ff_home = env.get("FACEFUSION_HOME")
        ff_conda_env = env.get("FACEFUSION_CONDA_ENV")
        ff_python = env.get("FACEFUSION_PYTHON", "python")

        if ff_home and not (Path(ff_home) / "facefusion.py").exists():
            self.logger.warning("Facefusion repository not found: %s", ff_home)
            raise FileNotFoundError(f"Facefusion не найден по пути: {ff_home}")

        use_cwd: str | None = None

        if ff_home and (Path(ff_home) / "facefusion.py").exists():
            use_cwd = ff_home
            if ff_conda_env:
                base_cmd = ["conda", "run", "-n", ff_conda_env, "python", "facefusion.py", "headless-run"]
            else:
                base_cmd = [ff_python, "facefusion.py", "headless-run"]
            command = base_cmd + [
                "-t", str(template),
                "-s", str(source),
                "-o", str(output),
            ]
        else:
            command = [
                "facefusion",
                "headless-run",
                "-t", str(template),
                "-s", str(source),
                "-o", str(output),
            ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=env,
                cwd=use_cwd,
                text=True,
            )
        except FileNotFoundError:
            self.logger.exception("facefusion CLI not found")
            raise RuntimeError(
                "Не найдена утилита 'facefusion'. Убедитесь, что она установлена и доступна в PATH."
            )

        if result.returncode != 0:
            self.logger.error("FaceFusion failed rc=%s stderr=%s", result.returncode, result.stderr[:1000])
            raise RuntimeError(
                f"FaceFusion завершился с ошибкой ({result.returncode}). stderr: {result.stderr[:4000]}"
            )

        if not output.exists() or output.stat().st_size == 0:
            self.logger.error("FaceFusion did not produce output: %s", output)
            raise RuntimeError("FaceFusion не создал выходной файл")