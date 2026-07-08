#!/usr/bin/env python3
"""Interactive 3D cube renderer for creating cube texture images.

Run this script to open an OpenCV window with a rotating 3D cube.
Press 'S' to save a screenshot of the current view to dataset/cubes/.
Press 'ESC' or 'Q' to exit.

Controls:
    Mouse drag - rotate the cube
    S          - save screenshot
    ESC / Q    - quit
"""
import os
import cv2
import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(TOOLS_DIR, "..", "dataset")
SAVE_DIR = os.path.join(DATASET_DIR, "cubes")

CUBE_NUMBER = "1"

os.makedirs(SAVE_DIR, exist_ok=True)

W, H = 600, 600
FOV = 400

vertices = np.array([
    [-100, -100, -100],
    [ 100, -100, -100],
    [ 100,  100, -100],
    [-100,  100, -100],
    [-100, -100,  100],
    [ 100, -100,  100],
    [ 100,  100,  100],
    [-100,  100,  100]
], dtype=np.float32)

render_vertices = vertices * 1.015

faces_flat = [
    0, 1, 2, 3,
    1, 5, 6, 2,
    5, 4, 7, 6,
    4, 0, 3, 7,
    4, 5, 1, 0,
    3, 2, 6, 7
]

angle_x, angle_y = 0.5, 0.5
is_dragging = False
last_mouse = (0, 0)


def make_texture(num_str):
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[:] = (0, 220, 255)
    cv2.rectangle(img, (30, 30), (170, 170), (0, 180, 230), -1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    size = cv2.getTextSize(num_str, font, 3, 8)[0]
    tx = (200 - size[0]) // 2
    ty = (200 + size[1]) // 2
    cv2.putText(img, num_str, (tx, ty), font, 3, (0, 0, 0), 8, cv2.LINE_AA)
    return img


textures = [make_texture(CUBE_NUMBER) for _ in range(6)]
src_pts = np.array([0, 0, 199, 0, 199, 199, 0, 199], dtype=np.float32).reshape(-1, 2)


def mouse_move(event, x, y, flags, param):
    global angle_x, angle_y, is_dragging, last_mouse
    if event == cv2.EVENT_LBUTTONDOWN:
        is_dragging = True
        last_mouse = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        is_dragging = False
    elif event == cv2.EVENT_MOUSEMOVE and is_dragging:
        dx = x - last_mouse[0]
        dy = y - last_mouse[1]
        angle_y += dx * 0.007
        angle_x += dy * 0.007
        last_mouse = (x, y)


cv2.namedWindow("Cube")
cv2.setMouseCallback("Cube", mouse_move)

img_counter = 0

while True:
    canvas = np.ones((H, W, 3), dtype=np.uint8) * 255

    rx = np.array([[1, 0, 0], [0, np.cos(angle_x), -np.sin(angle_x)], [0, np.sin(angle_x), np.cos(angle_x)]])
    ry = np.array([[np.cos(angle_y), 0, np.sin(angle_y)], [0, 1, 0], [-np.sin(angle_y), 0, np.cos(angle_y)]])
    rot = np.dot(rx, ry)

    rot_v = np.dot(render_vertices, rot.T)
    rot_v_exact = np.dot(vertices, rot.T)

    face_list = []
    for i in range(6):
        v_idx = faces_flat[i*4 : i*4+4]
        z_center = np.mean([rot_v_exact[v][2] for v in v_idx])
        face_list.append((z_center, i, v_idx))

    face_list.sort(key=lambda item: item[0], reverse=True)

    for z_center, face_idx, v_idx in face_list:
        pts_2d = []
        for v in v_idx:
            x3d, y3d, z3d = rot_v[v]
            dist = 400 + z3d
            x2d = int(W / 2 + (x3d * FOV) / dist)
            y2d = int(H / 2 + (y3d * FOV) / dist)
            pts_2d.append([x2d, y2d])

        dst_pts = np.array(pts_2d, dtype=np.float32)
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(textures[face_idx], M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 220, 255))

        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillConvexPoly(mask, dst_pts.astype(np.int32), 255)
        canvas[mask > 0] = warped[mask > 0]
        cv2.polylines(canvas, [dst_pts.astype(np.int32)], True, (0, 220, 255), 2, cv2.LINE_AA)

    cv2.imshow("Cube", canvas)

    key = cv2.waitKey(16) & 0xFF

    if key == ord('s') or key == ord('ы'):
        filename = f"cube_{CUBE_NUMBER}_{img_counter:04d}.jpg"
        full_path = os.path.join(SAVE_DIR, filename)
        cv2.imwrite(full_path, canvas)
        print(f"Saved: {full_path}")
        img_counter += 1
    elif key == 27 or key == ord('q') or cv2.getWindowProperty("Cube", cv2.WND_PROP_VISIBLE) < 1:
        break

cv2.destroyAllWindows()
