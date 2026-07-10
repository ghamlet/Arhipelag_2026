#!/usr/bin/env python3
"""Проверка изображений на соответствие требованиям.

Требования:
- Формат изображений — *.jpg
- Разрешение не менее 640×480 пикселей
"""

import sys
from pathlib import Path

from PIL import Image

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"
FOLDERS = [ "no_object_fix_size"]
MIN_WIDTH = 640
MIN_HEIGHT = 480


def check_image(path: Path) -> list[str]:
    errors: list[str] = []

    if path.suffix.lower() != ".jpg":
        errors.append(f"Неверный формат: {path.suffix} (ожидается .jpg)")

    try:
        with Image.open(path) as img:
            width, height = img.size
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                errors.append(f"Разрешение {width}×{height} < {MIN_WIDTH}×{MIN_HEIGHT}")
    except Exception as e:
        errors.append(f"Не удалось открыть изображение: {e}")

    return errors


def main() -> int:
    total = 0
    failed = 0

    for folder_name in FOLDERS:
        folder = DATASET_DIR / folder_name
        if not folder.is_dir():
            print(f"[SKIP] Папка не найдена: {folder}")
            continue

        images = sorted(folder.glob("*.*"))
        for img_path in images:
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}:
                continue
            total += 1
            errors = check_image(img_path)
            if errors:
                failed += 1
                print(f"[FAIL] {img_path.relative_to(DATASET_DIR)}")
                for err in errors:
                    print(f"       → {err}")

    print(f"\nИтого: {total} изображений, {failed} не прошли проверку")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
