#!/usr/bin/env python3
from user.library import DroneLibrary
import math
import time

# Функция для разворота дрона на месте
def rotation(drone):
    # Временный счётчик пройденных углов
    angle = 0
    # Шаг в градусах
    step = 3
    
    # Разворот на месте, линейная скорость 0
    drone.set_speed(0)
    time.sleep(1)
    
    # Меняем угол, пока не наберётся 360 градусов (1 оборот)
    while angle < 360:
        # Изменим текущий курс дрона на заданный шаг
        drone.change_course(step)
        # Небольшая пауза в 50 мс
        time.sleep(0.05)
        # Учтём пройденный угол
        angle = angle + step

# Точка входа в приложение
if __name__ == "__main__":
    # Создаём объект библиотеки управления дроном
    drone = DroneLibrary()
    # Включаемся в управление вместо джойстика
    drone.start()
    # Выполняем разворот на 360
    rotation(drone)
    # Отключаемся от управления
    drone.stop()