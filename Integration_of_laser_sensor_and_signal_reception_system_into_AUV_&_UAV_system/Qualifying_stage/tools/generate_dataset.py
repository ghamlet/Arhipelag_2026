#!/usr/bin/env python3
"""Dataset image generator.

Composites cube images onto backgrounds and applies random underwater
distortion filters (illumination, turbidity, glare, particles, color tint).
Generates NUM_IMAGES images into dataset/black_box/.

Also exposes apply_* filter functions for use by filter_lab.py.
"""
import os
import random
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(TOOLS_DIR, "..", "dataset")
NO_OBJECT_DIR = os.path.join(DATASET_DIR, "no_object")
CUBES_DIR = os.path.join(DATASET_DIR, "cubes")
OUTPUT_DIR = os.path.join(DATASET_DIR, "black_box")

NUM_IMAGES = 20
WHITE_THRESHOLD = 240


def apply_illumination(img, strength=None):
    """Adjust image brightness to simulate underwater lighting conditions.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Brightness multiplier. 0.5 = darker, 1.0 = original,
                  1.3 = brighter. If None, random in [0.5, 1.3].

    Returns:
        PIL Image with adjusted brightness.
    """
    if strength is None:
        strength = random.uniform(0.5, 1.3)
    return ImageEnhance.Brightness(img).enhance(strength)


def apply_turbidity(img, strength=None):
    """Simulate water turbidity by adding blur.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Blur radius. 0.0 = no blur, higher = more turbid water.
                  If None, random in [0.0, 4.0].

    Returns:
        PIL Image with turbidity effect applied.
    """
    if strength is None:
        strength = random.uniform(0.0, 4.0)
    if strength < 0.1:
        return img
    return img.filter(ImageFilter.GaussianBlur(radius=strength))


def apply_glare(img, strength=None):
    """Add bright glare spots to simulate underwater light reflections.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Number of glare spots (0.0 = none, higher = more glare).
                  If None, random in [0, 5].

    Returns:
        PIL Image with glare spots added.
    """
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
    """Add suspended particles (marine snow) to simulate dirty water.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Particle density multiplier. 0.0 = no particles,
                  1.0 = default density. If None, random in [0.0, 3.0].

    Returns:
        PIL Image with suspended particles.
    """
    if strength is None:
        strength = random.uniform(0.0, 3.0)
    if strength < 0.05:
        return img
    base_density = 0.0003
    density = base_density * strength
    arr = np.array(img, dtype=np.float32)
    w, h = img.size
    num_particles = int(w * h * density)
    for _ in range(num_particles):
        px = random.randint(0, w - 1)
        py = random.randint(0, h - 1)
        size = random.randint(1, 2)
        brightness = random.randint(180, 255)
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                nx, ny = px + dx, py + dy
                if 0 <= nx < w and 0 <= ny < h:
                    fade = 1.0 - (abs(dx) + abs(dy)) / (size * 2 + 1)
                    for c in range(3):
                        arr[ny, nx, c] = min(255, arr[ny, nx, c] + brightness * fade * 0.5)
    return Image.fromarray(arr.astype(np.uint8))


def apply_blue_filter(img, strength=None):
    """Apply blue color filter to simulate deep water conditions.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Filter intensity. 0.0 = no effect, 1.0 = strong blue tint.
                  If None, random in [0.2, 0.8].

    Returns:
        PIL Image with blue color cast.
    """
    if strength is None:
        strength = random.uniform(0.2, 0.8)
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 - strength * 0.4), 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 - strength * 0.1), 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 + strength * 0.5), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_green_filter(img, strength=None):
    """Apply green color filter to simulate algae-rich or shallow water.

    Args:
        img: Input PIL Image in RGB mode.
        strength: Filter intensity. 0.0 = no effect, 1.0 = strong green tint.
                  If None, random in [0.2, 0.8].

    Returns:
        PIL Image with green color cast.
    """
    if strength is None:
        strength = random.uniform(0.2, 0.8)
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 - strength * 0.15), 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 + strength * 0.3), 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - strength * 0.2), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bg = Image.open(os.path.join(NO_OBJECT_DIR, "image.png")).convert("RGBA")
    bg_w, bg_h = bg.size

    cube_files = sorted([f for f in os.listdir(CUBES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))])

    cubes = []
    for cf in cube_files:
        img = Image.open(os.path.join(CUBES_DIR, cf)).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for r, g, b, a in datas:
            if r >= WHITE_THRESHOLD and g >= WHITE_THRESHOLD and b >= WHITE_THRESHOLD:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        cubes.append(img)

    for i in range(NUM_IMAGES):
        result = bg.copy()
        cube = random.choice(cubes)
        cw, ch = cube.size
        x = random.randint(0, max(0, bg_w - cw))
        y = random.randint(0, max(0, bg_h - ch))
        result.paste(cube, (x, y), cube)

        result = result.convert("RGB")
        result = apply_illumination(result)
        result = apply_turbidity(result)
        result = apply_glare(result)
        result = apply_particles(result)

        if random.random() < 0.5:
            result = apply_blue_filter(result)
        else:
            result = apply_green_filter(result)

        result.save(os.path.join(OUTPUT_DIR, f"img_{i:04d}.png"))
        print(f"Saved img_{i:04d}.png")

    print(f"\nDone! Generated {NUM_IMAGES} images in {OUTPUT_DIR}")
