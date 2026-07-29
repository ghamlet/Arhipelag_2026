#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Просмотр видео с камеры дрона Океаника через ROS Bridge.
Подключается к дрону по WiFi и отображает топик /raspicam_node/image/compressed
"""

import base64
import cv2
import logging
import numpy as np
import roslibpy

DRONE_IP = '192.168.88.155'
ROS_BRIDGE_PORT = 9090
CAMERA_TOPIC = '/raspicam_node/image/compressed'



def on_image(msg):
    try:
        base64_bytes = msg['data'].encode('ascii')
        raw_bytes = base64.b64decode(base64_bytes)
        img_buffer = np.frombuffer(raw_bytes, dtype=np.uint8)
        image = cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)

        if image is not None:
            cv2.imshow('Drone Camera', image)
            cv2.waitKey(1)
        else:
            log.warning('Failed to decode image')
    except Exception as e:
        log.error(f'Error processing image: {e}')


def main():
    fmt = '%(asctime)s %(levelname)8s: %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO)
    global log
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
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()