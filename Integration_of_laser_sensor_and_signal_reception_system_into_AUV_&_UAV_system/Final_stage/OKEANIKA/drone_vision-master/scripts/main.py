#!/usr/bin/env python3
# *-* coding: utf-8 -*-

"""!
@file main.py
@brief Внешняя нода распознавания цифр в видео потоке от ноды raspicam
"""


import base64
import cv2
import logging
import numpy as np
import roslibpy
import time
from ai_edge_litert.interpreter import Interpreter

MODEL_PATH = 'models/model_compatible.tflite'


class DroneVision:
    def __init__(self):
        self.interpreter = Interpreter(model_path=MODEL_PATH)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.size = self.input_details[0]['shape'][1], self.input_details[0]['shape'][2]

    def receive_image(self, img):
        log.info('Received image seq=%d', img['header']['seq'])
        base64_bytes = img['data'].encode('ascii')
        raw_bytes = base64.b64decode(base64_bytes)
        img_buffer = np.frombuffer(raw_bytes, dtype=np.uint8)
        image = cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, self.size)
        input_data = np.expand_dims(resized.astype('float32') / 255.0, axis=0)

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        predicted_digit = np.argmax(output_data[0])
        confidence = np.max(output_data[0])

        if confidence > 0.80:
            log.info(f"[{time.strftime('%H:%M:%S')}] ЦИФРА: {predicted_digit} ({confidence*100:.1f}%)")
            cv2.imwrite(f"output/detected_{predicted_digit}_{int(time.time())}.jpg", image)

    def run(self):
        client = roslibpy.Ros(host='192.168.88.155', port=9090)
        subscriber = roslibpy.Topic(client, '/raspicam_node/image/compressed', 'sensor_msgs/CompressedImage', throttle_rate=1000)
        subscriber.subscribe(dv.receive_image)
        client.run_forever()


if __name__ == '__main__':
    fmt = '%(asctime)s %(levelname)8s: %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO)
    log = logging.getLogger('DroneVision')
    dv = DroneVision()
    dv.run()
