#!/usr/bin/env python3
# *-* coding: utf-8 -*-

"""!
@file drone_user_client.py
@brief Внешняя нода для взаимодействия с внутренним drone_user_server.py
"""


import logging
import roslibpy
import time

def callback(result):
    # Вызывается в случае успешного получения ответа от сервера.
    log.info(f'async response str={result["str"]}')


def errback(err):
    # Вызывается в случае ошибки.
    log.error(f'async error: {err}')


def run():
    client = roslibpy.Ros(host='192.168.88.155', port=9090)
    client.run()

    service = roslibpy.Service(client, '/drone_user_service', 'drone/DroneUserService')

    # Создать блокирующий запрос в сервис.
    try:
        response = service.call(roslibpy.ServiceRequest({'str': 'query'}), timeout=30)
        log.info(f'sync response str={response["str"]}')
    except roslibpy.core.RosTimeoutError as e:
        log.error(f'sync response err: {e}')

    # Создать неблокирующий запрос в сервис.
    service.call(roslibpy.ServiceRequest({'str': 'test'}), callback=callback, errback=errback)

    # Подождем немного... здесь может быть главный цикл приложения.
    time.sleep(5)

    # Закончили работу с ROS.
    client.terminate()


if __name__ == '__main__':
    fmt = '%(asctime)s %(levelname)8s: %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO)
    log = logging.getLogger('DroneUserClient')
    run()
