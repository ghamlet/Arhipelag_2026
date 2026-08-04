#!/usr/bin/env python3
"""
Search Pattern: Spiral (Спираль) - Расширяющийся спиральный поиск

AUV выполняет спиральное движение от центральной точки с увеличением радиуса.
Подходит для: поиска объекта от известной позиции, обследование круглых участков,
систематичное покрытие площади вокруг точки.

Использует: set_depth, change_course (плавное изменение курса), set_speed, get_depth
"""

import time
import math
from user.library import DroneLibrary


class SpiralSurvey:
    def __init__(self, drone, center_depth_m, max_radius_m, radius_step_m, 
                 speed_pct, turns_per_layer=1):
        self.drone = drone
        self.center_depth = center_depth_m      # глубина центра (м)
        self.max_radius = max_radius_m          # максимальный радиус спирали (м)
        self.radius_step = radius_step_m        # увеличение радиуса за виток (м)
        self.speed = speed_pct                  # скорость (0-100%)
        self.turns_per_layer = turns_per_layer  # витков на слой
        
        self.step_angle = 5      # градусов на шаг (маленький для плавности)
        self.step_time = 0.2     # время между шагами

    def dive(self):
        """Ныряем на заданную глубину"""
        print(f"[Spiral] Ныряем на глубину {self.center_depth} м...")
        self.drone.set_depth(self.center_depth)
        time.sleep(3)

    def rise(self):
        """Всплываем"""
        print("[Spiral] Всплываем...")
        self.drone.set_depth(0)
        time.sleep(2)

    def run(self):
        """Выполнение спирального обследования"""
        self.dive()
        self.drone.set_speed(self.speed)
        
        print(f"[Spiral] Начинаем спираль: R_max={self.max_radius}м, шаг={self.radius_step}м/виток, скорость={self.speed}%")
        
        total_angle = 0
        current_radius = 0
        max_total_angle = int((self.max_radius / self.radius_step) * 360 * self.turns_per_layer)
        
        while total_angle < max_total_angle:
            # Радиус увеличивается линейно с углом
            current_radius = (total_angle / 360) * self.radius_step * self.turns_per_layer
            
            if current_radius > self.max_radius:
                current_radius = self.max_radius
            
            # Плавное изменение курса для создания спирали
            # Угловая скорость = step_angle / step_time
            # Линейная скорость = angular_speed * radius
            # Для постоянной линейной скорости меняем угловую скорость
            
            course_change_rate = self.step_angle * (self.speed * 0.01)  # адаптивный шаг
            self.drone.change_course(course_change_rate)
            
            total_angle += self.step_angle
            
            # Прогресс каждые 90 градусов
            if total_angle % 90 == 0:
                current_depth = self.drone.get_depth() / 100.0
                print(f"[Spiral] Угол: {total_angle}°, Радиус: {current_radius:.1f}м, Глубина: {current_depth:.2f}м")
            
            time.sleep(self.step_time)
            
            if current_radius >= self.max_radius and total_angle > 360:
                break
        
        self.drone.set_speed(0)
        self.rise()
        print("[Spiral] Спиральное обследование завершено")


def main():
    # === ПАРАМЕТРЫ СПИРАЛИ ===
    CENTER_DEPTH = 5       # метры
    MAX_RADIUS = 15        # метры (макс радиус)
    RADIUS_STEP = 2        # метры за виток
    SPEED = 40             # % скорости
    TURNS_PER_LAYER = 1    # витков на слой
    
    drone = DroneLibrary()
    drone.start(takecontrol=True)
    
    try:
        spiral = SpiralSurvey(drone, CENTER_DEPTH, MAX_RADIUS, RADIUS_STEP, SPEED, TURNS_PER_LAYER)
        spiral.run()
    except KeyboardInterrupt:
        print("\n[Spiral] Прервано пользователем")
    finally:
        drone.stop()
        print("[Spiral] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()