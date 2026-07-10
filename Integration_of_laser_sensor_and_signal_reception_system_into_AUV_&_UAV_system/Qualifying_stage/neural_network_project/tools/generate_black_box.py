#!/usr/bin/env python3
"""Generate synthetic dataset images for black_box/digit_i folders.

For each digit:
  - Uses 200-400 random backgrounds from no_object_fix_size/
  - For each background, generates multiple images (3-5 filter combos)
  - Places 1-3 random cube images from cubes/digit_i/ onto each background
  - Applies random filter combinations from generate_dataset.py
  - Saves at least 1000 images per digit into black_box/digit_i/
"""
import os
import random
import sys
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(TOOLS_DIR, "..", "dataset")
NO_OBJECT_DIR = os.path.join(DATASET_DIR, "no_object_fix_size")
CUBES_BASE = os.path.join(DATASET_DIR, "cubes")
OUTPUT_BASE = os.path.join(DATASET_DIR, "black_box")

WHITE_THRESHOLD = 240
MAX_IMAGES = 1200


def remove_white_bg(img):
    """Replace near-white pixels with transparent."""
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for r, g, b, a in datas:
        if r >= WHITE_THRESHOLD and g >= WHITE_THRESHOLD and b >= WHITE_THRESHOLD:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def apply_illumination(img, strength=None):
    if strength is None:
        strength = random.uniform(0.6, 1.2)
    return ImageEnhance.Brightness(img).enhance(strength)


def apply_turbidity(img, strength=None):
    if strength is None:
        strength = random.uniform(0.0, 2.5)
    if strength < 0.1:
        return img
    return img.filter(ImageFilter.GaussianBlur(radius=strength))


def apply_glare(img, strength=None):
    if strength is None:
        strength = random.uniform(0, 3)
    num_spots = max(0, round(strength))
    if num_spots == 0:
        return img
    arr = np.array(img, dtype=np.float32)
    w, h = img.size
    for _ in range(num_spots):
        cx = random.randint(0, w - 1)
        cy = random.randint(0, h - 1)
        radius = random.randint(30, 90)
        intensity = random.uniform(0.2, 0.6)
        yy, xx = np.ogrid[:h, :w]
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        mask = np.clip(1.0 - dist / radius, 0, 1) * intensity
        for c in range(3):
            arr[:, :, c] = np.clip(arr[:, :, c] + mask * 255, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_particles(img, strength=None):
    if strength is None:
        strength = random.uniform(0.0, 1.5)
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
    if strength is None:
        strength = random.uniform(0.1, 0.5)
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 - strength * 0.4), 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 - strength * 0.1), 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 + strength * 0.5), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_green_filter(img, strength=None):
    if strength is None:
        strength = random.uniform(0.1, 0.5)
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 - strength * 0.15), 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 + strength * 0.3), 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - strength * 0.2), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_contrast(img, strength=None):
    if strength is None:
        strength = random.uniform(0.7, 1.3)
    return ImageEnhance.Contrast(img).enhance(strength)


def apply_color_jitter(img):
    """Randomly adjust hue/saturation slightly."""
    if random.random() < 0.5:
        img = ImageEnhance.Color(img).enhance(random.uniform(0.7, 1.3))
    return img


def build_filter_chain():
    """Build a random filter chain. Each filter has a chance to be applied
    with reduced parameters to avoid killing the image quality."""
    chain = []

    # illumination always applied
    chain.append(("illumination", random.uniform(0.6, 1.2)))

    # turbidity: 60% chance, mild
    if random.random() < 0.6:
        chain.append(("turbidity", random.uniform(0.0, 2.0)))

    # glare: 40% chance
    if random.random() < 0.4:
        chain.append(("glare", random.uniform(0, 2)))

    # particles: 50% chance
    if random.random() < 0.5:
        chain.append(("particles", random.uniform(0.0, 1.2)))

    # color tint: 70% chance
    if random.random() < 0.7:
        tint = random.choice(["blue", "green"])
        chain.append((tint, random.uniform(0.1, 0.4)))

    # contrast: 40% chance
    if random.random() < 0.4:
        chain.append(("contrast", random.uniform(0.8, 1.2)))

    # color jitter: 30% chance
    if random.random() < 0.3:
        chain.append(("color_jitter", None))

    return chain


def apply_filters(img, chain):
    """Apply a pre-built filter chain to an image."""
    for name, strength in chain:
        if name == "illumination":
            img = apply_illumination(img, strength)
        elif name == "turbidity":
            img = apply_turbidity(img, strength)
        elif name == "glare":
            img = apply_glare(img, strength)
        elif name == "particles":
            img = apply_particles(img, strength)
        elif name == "blue":
            img = apply_blue_filter(img, strength)
        elif name == "green":
            img = apply_green_filter(img, strength)
        elif name == "contrast":
            img = apply_contrast(img, strength)
        elif name == "color_jitter":
            img = apply_color_jitter(img)
    return img


def load_cubes(cubes_dir):
    """Load and prepare cube images with white background removed."""
    cube_files = sorted([f for f in os.listdir(cubes_dir)
                         if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    cubes = []
    for cf in cube_files:
        img = Image.open(os.path.join(cubes_dir, cf))
        img = remove_white_bg(img)
        cubes.append(img)
    return cubes


def place_cube(bg, cube):
    """Place exactly 1 cube onto the background at original size."""
    result = bg.copy()
    bg_w, bg_h = result.size
    cw, ch = cube.size
    x = random.randint(0, max(0, bg_w - cw))
    y = random.randint(0, max(0, bg_h - ch))
    result.paste(cube, (x, y), cube)
    return result


def generate_digit(digit_num):
    """Generate at most MAX_IMAGES images for one digit."""
    cubes_dir = os.path.join(CUBES_BASE, f"digit_{digit_num}")
    output_dir = os.path.join(OUTPUT_BASE, f"digit_{digit_num}")
    os.makedirs(output_dir, exist_ok=True)

    existing = [f for f in os.listdir(output_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    start_idx = len(existing)
    remaining = MAX_IMAGES - start_idx
    if remaining <= 0:
        print(f"  digit_{digit_num} already has {start_idx} images, skipping.")
        return 0

    cubes = load_cubes(cubes_dir)
    if not cubes:
        print(f"  WARNING: No cubes found in {cubes_dir}, skipping.")
        return 0

    # load all available backgrounds
    bg_files = [f for f in os.listdir(NO_OBJECT_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    backgrounds = []
    for bf in bg_files:
        img = Image.open(os.path.join(NO_OBJECT_DIR, bf)).convert("RGB")
        backgrounds.append(img)

    print(f"  Loaded {len(backgrounds)} backgrounds, {len(cubes)} cubes")

    saved = 0
    # first pass: each background once
    for bg in backgrounds:
        if saved >= remaining:
            break
        cube = random.choice(cubes)
        composited = place_cube(bg, cube)
        chain = build_filter_chain()
        result = apply_filters(composited, chain)

        idx = start_idx + saved
        result.save(os.path.join(output_dir, f"img_{idx:05d}.png"))
        saved += 1
        if saved % 100 == 0:
            print(f"    {saved} images generated...")

    # second pass: reuse backgrounds with different cubes/filters until MAX_IMAGES
    while saved < remaining:
        bg = random.choice(backgrounds)
        cube = random.choice(cubes)
        composited = place_cube(bg, cube)
        chain = build_filter_chain()
        result = apply_filters(composited, chain)

        idx = start_idx + saved
        result.save(os.path.join(output_dir, f"img_{idx:05d}.png"))
        saved += 1
        if saved % 100 == 0:
            print(f"    {saved} images generated...")

    total = start_idx + saved
    print(f"  Done! digit_{digit_num}: {saved} new images (total: {total})")
    return saved


def main():
    print("=" * 60)
    print("Black Box Dataset Generator")
    print("=" * 60)

    # process each digit 1-9
    for digit in range(1, 10):
        print(f"\n--- Processing digit_{digit} ---")
        count = generate_digit(digit)
        print(f"  Saved {count} images to {OUTPUT_BASE}/digit_{digit}/")

    print("\n" + "=" * 60)
    print("All digits processed!")

    # summary
    print("\nFinal counts:")
    for digit in range(1, 10):
        d = os.path.join(OUTPUT_BASE, f"digit_{digit}")
        if os.path.exists(d):
            n = len([f for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
            print(f"  digit_{digit}: {n} images")


if __name__ == "__main__":
    main()
