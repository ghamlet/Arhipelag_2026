#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Скрипт для просмотра и ЗАПИСИ видео с камеры дрона через rosbridge с автоименованием."""

import base64
import os
import cv2
import logging
import numpy as np
import roslibpy
from datetime import datetime

DRONE_IP = '192.168.88.155'
ROS_BRIDGE_PORT = 9090
CAMERA_TOPIC = '/raspicam_node/image/compressed'

# Целевая папка для сохранения записей
TARGET_DIR = '/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/records'
VIDEO_FPS = 20.0  # Скорость записи видео

# Глобальные переменные
video_writer = None  
video_output_path = ''


def on_image(msg):
    global video_writer, video_output_path
    try:
        base64_bytes = msg['data'].encode('ascii')
        raw_bytes = base64.b64decode(base64_bytes)
        img_buffer = np.frombuffer(raw_bytes, dtype=np.uint8)
        image = cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)

        if image is not None:
            # Инициализируем запись при получении самого первого кадра
            if video_writer is None:
                # Создаем папку, если она не существует
                os.makedirs(TARGET_DIR, exist_ok=True)
                
                # Генерируем уникальное имя файла на основе текущего времени
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                video_output_path = os.path.join(TARGET_DIR, f'video_{timestamp}.mp4')
                
                height, width, _ = image.shape
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(video_output_path, fourcc, VIDEO_FPS, (width, height))
                log.info(f'Started video recording to: {video_output_path} ({width}x{height} @ {VIDEO_FPS} FPS)')

            # Записываем текущий кадр в файл
            video_writer.write(image)

            # Отображаем на экране
            cv2.imshow('Drone Camera', image)
            cv2.waitKey(1)
        else:
            log.warning('Failed to decode image')
    except Exception as e:
        log.error(f'Error processing image: {e}')


def main():
    fmt = '%(asctime)s %(levelname)8s: %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO)
    global log, video_writer
    log = logging.getLogger('DroneCameraViewer')

    log.info(f'Connecting to {DRONE_IP}:{ROS_BRIDGE_PORT}...')

    client = roslibpy.Ros(host=DRONE_IP, port=ROS_BRIDGE_PORT)

    subscriber = roslibpy.Topic(
        client,
        CAMERA_TOPIC,
        'sensor_msgs/CompressedImage',
        throttle_rate=100
    )
    subscriber.subscribe(on_image)

    try:
        client.run_forever()
    except KeyboardInterrupt:
        log.info('Shutting down...')
    finally:
        subscriber.unsubscribe()
        client.terminate()
        
        # Безопасно закрываем файл
        if video_writer is not None:
            video_writer.release()
            log.info(f'Video recording saved to {video_output_path}')
            
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
