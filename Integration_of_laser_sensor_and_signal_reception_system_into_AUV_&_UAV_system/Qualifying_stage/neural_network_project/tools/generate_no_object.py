#!/usr/bin/env python3
"""Generate no_object dataset with underwater distortion filters.

Applies random combinations of: illumination, turbidity, glare, particles.
Excludes green and blue color filters.
Target: 2000+ images in dataset/no_object_new/.
"""
import os
import random
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(TOOLS_DIR, "..", "dataset")
INPUT_DIR = os.path.join(DATASET_DIR, "no_object_fix_size")
OUTPUT_DIR = os.path.join(DATASET_DIR, "no_object_new")

TARGET_COUNT = 2100


def apply_illumination(img, strength=None):
    if strength is None:
        strength = random.uniform(0.5, 1.3)
    return ImageEnhance.Brightness(img).enhance(strength)


def apply_turbidity(img, strength=None):
    if strength is None:
        strength = random.uniform(0.0, 4.0)
    if strength < 0.1:
        return img
    return img.filter(ImageFilter.GaussianBlur(radius=strength))


def apply_glare(img, strength=None):
    if strength is None:
        strength = random.uniform(0, 5)
    num_spots = max(0, round(strength))
    if num_spots == 0:
        return img
    arr = np.array(img, dtype=np.float32)
    w, h = img.size
    for _ in range(num_spots):
        cx = random.randint(0, w - 1)
        cy = random.randint(0, h - 1)
        radius = random.randint(30, 120)
        intensity = random.uniform(0.3, 0.8)
        yy, xx = np.ogrid[:h, :w]
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        mask = np.clip(1.0 - dist / radius, 0, 1) * intensity
        for c in range(3):
            arr[:, :, c] = np.clip(arr[:, :, c] + mask * 255, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_particles(img, strength=None):
    if strength is None:
        strength = random.uniform(0.0, 3.0)
    if strength < 0.05:
        return img
    arr = np.array(img, dtype=np.float32)
    w, h = img.size
    num_particles = int(w * h * 0.0003 * strength)
    if num_particles == 0:
        return img
    px = np.random.randint(0, w, num_particles)
    py = np.random.randint(0, h, num_particles)
    vals = np.random.randint(180, 256, num_particles).astype(np.float32)
    for i in range(num_particles):
        x, y = int(px[i]), int(py[i])
        arr[y, x] = np.clip(arr[y, x] + vals[i] * 0.5, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


FILTERS = [apply_illumination, apply_turbidity, apply_glare, apply_particles]


def get_random_params(filter_fn):
    name = filter_fn.__name__
    if name == "apply_illumination":
        return random.uniform(0.5, 1.3)
    elif name == "apply_turbidity":
        return random.uniform(0.0, 4.0)
    elif name == "apply_glare":
        return random.uniform(0, 5)
    elif name == "apply_particles":
        return random.uniform(0.0, 3.0)
    return None


def is_near_max(name, value):
    if value is None:
        return False
    if name == "apply_illumination":
        return value > 1.2
    elif name == "apply_turbidity":
        return value > 3.5
    elif name == "apply_glare":
        return value > 4
    elif name == "apply_particles":
        return value > 2.5
    return False


def apply_filters(img):
    num_filters = random.choices([1, 2, 3], weights=[3, 4, 3])[0]
    chosen = random.sample(FILTERS, num_filters)
    max_used = False
    for fn in chosen:
        param = get_random_params(fn)
        if max_used and is_near_max(fn.__name__, param):
            param = None
        if is_near_max(fn.__name__, param):
            max_used = True
        img = fn(img, param)
    return img


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(INPUT_DIR)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    print(f"Found {len(files)} source images in {INPUT_DIR}")

    count = 0
    while count < TARGET_COUNT:
        for fname in files:
            if count >= TARGET_COUNT:
                break
            src = os.path.join(INPUT_DIR, fname)
            img = Image.open(src).convert("RGB")
            result = apply_filters(img)
            out_name = f"img_{count:04d}.jpg"
            result.save(os.path.join(OUTPUT_DIR, out_name), quality=95)
            count += 1
            if count % 100 == 0:
                print(f"  Generated {count}/{TARGET_COUNT}")

    print(f"\nDone! Generated {count} images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
