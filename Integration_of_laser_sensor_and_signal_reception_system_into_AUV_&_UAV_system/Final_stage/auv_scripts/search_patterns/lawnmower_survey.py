#!/usr/bin/env python3
"""
Search Pattern: Lawnmower (Газонокосилка) - Прямолинейное сканирование

AUV выполняет параллельные проходы с разворотами 180° на границах.
Подходит для обследования прямоугольных участков: трубопроводы, дно, картографирование.

Использует: set_depth, set_course, change_course, set_speed, get_depth, get_course
"""

import time
from user.library import DroneLibrary


class LawnmowerSurvey:
    def __init__(self, drone, survey_width_m, survey_length_m, line_spacing_m, 
                 speed_pct, depth_m, turn_time_s=3.0):
        self.drone = drone
        self.survey_width = survey_width_m      # ширина области (м)
        self.survey_length = survey_length_m    # длина области (м)
        self.line_spacing = line_spacing_m      # шаг между линиями (м)
        self.speed = speed_pct                  # скорость (0-100%)
        self.depth = depth_m                    # глубина (м)
        self.turn_time = turn_time_s            # время на разворот 180° (сек)
        
        self.num_lines = int(survey_width_m / line_spacing_m) + 1
        self.current_line = 0
        self.direction = 1  # 1 = forward, -1 = backward

    def dive(self):
        """Ныряем на заданную глубину"""
        print(f"[Lawnmower] Ныряем на глубину {self.depth} м...")
        self.drone.set_depth(self.depth)
        time.sleep(3)

    def rise(self):
        """Всплываем на поверхность"""
        print("[Lawnmower] Всплываем...")
        self.drone.set_depth(0)
        time.sleep(2)

    def move_forward_distance(self, distance_m):
        """Двигаемся вперед на заданное расстояние (прибл. по времени)"""
        # Примерная скорость: speed% ~ 0.1 м/с при 100%
        est_speed_ms = max(self.speed * 0.01, 0.2)
        move_time = distance_m / est_speed_ms
        
        print(f"[Lawnmower] Движение {distance_m:.1f} м (~{move_time:.0f}с на скорости {self.speed}%)")
        self.drone.set_speed(self.speed)
        time.sleep(move_time)
        self.drone.set_speed(0)
        time.sleep(0.5)

    def turn_180(self, direction='left'):
        """Разворот на 180 градусов"""
        angle = 180 if direction == 'left' else -180
        print(f"[Lawnmower] Разворот {angle}°...")
        self.drone.change_course(angle)
        time.sleep(self.turn_time)

    def lateral_shift(self, distance_m):
        """Боковой сдвиг для перехода на следующую линию"""
        est_speed_ms = max(self.speed * 0.01, 0.15)
        move_time = distance_m / est_speed_ms
        
        print(f"[Lawnmower] Боковой сдвиг {distance_m:.1f} м...")
        self.drone.set_speed(self.speed)
        time.sleep(move_time)
        self.drone.set_speed(0)
        time.sleep(0.5)

    def run(self):
        """Выполнение газонокосильного обследования"""
        self.dive()
        
        print(f"[Lawnmower] Начинаем обследование: {self.num_lines} линий, длина {self.survey_length}м, шаг {self.line_spacing}м")
        
        for line_num in range(self.num_lines):
            print(f"\n[Lawnmower] === ЛИНИЯ {line_num + 1}/{self.num_lines} ===")
            
            # Движение вдоль длины области
            self.move_forward_distance(self.survey_length)
            
            if line_num < self.num_lines - 1:
                # На конце линии: разворот 180°
                turn_dir = 'left' if self.direction > 0 else 'right'
                self.turn_180(turn_dir)
                
                # Боковой сдвиг на шаг между линиями
                self.lateral_shift(self.line_spacing)
                
                # Еще один разворот 180° для следующей линии
                self.turn_180(turn_dir)
                
                # Меняем направление
                self.direction *= -1
            
            # Проверка глубины каждую линию
            current_depth = self.drone.get_depth()
            print(f"[Lawnmower] Контроль глубины: {current_depth/100:.2f} м (цель: {self.depth} м)")
        
        self.drone.set_speed(0)
        self.rise()
        print("[Lawnmower] Обследование завершено")


def main():
    # === ПАРАМЕТРЫ ОБСЛЕДОВАНИЯ ===
    SURVEY_WIDTH = 20     # метры (ширина участка)
    SURVEY_LENGTH = 30    # метры (длина участка) 
    LINE_SPACING = 3      # метры (шаг между линиями)
    SPEED = 50            # % скорости
    DEPTH = 5             # метры глубины
    TURN_TIME = 3.0       # секунды на разворот 180°
    
    drone = DroneLibrary()
    drone.start(takecontrol=True)
    
    try:
        survey = LawnmowerSurvey(drone, SURVEY_WIDTH, SURVEY_LENGTH, 
                                 LINE_SPACING, SPEED, DEPTH, TURN_TIME)
        survey.run()
    except KeyboardInterrupt:
        print("\n[Lawnmower] Прервано пользователем")
    finally:
        drone.stop()
        print("[Lawnmower] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()