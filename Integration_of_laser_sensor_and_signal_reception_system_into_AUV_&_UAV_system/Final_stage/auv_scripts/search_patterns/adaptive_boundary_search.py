#!/usr/bin/env python3
"""
Search Pattern: Adaptive Boundary Search (Адаптивный поиск с границами)

AUV выполняет поиск в заданных прямоугольных границах с:
- Обнаружением и избеганием границ
- Адаптивным шагом между линиями (с учетом дальности датчика)
- Приоритетными зонами (чаще посещаются)
- Возвратом на базу при нарушении границ или низком заряде
- Остановкой при находке объекта (флаг cube_found)

Использует: set_depth, set_course, change_course, set_speed, get_depth, get_course
"""

import time
from user.library import DroneLibrary


class Boundary:
    """Прямоугольная граница бассейна"""
    def __init__(self, min_x, max_x, min_y, max_y):
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y

    def contains(self, x, y, margin=1.0):
        return (self.min_x + margin <= x <= self.max_x - margin and
                self.min_y + margin <= y <= self.max_y - margin)

    def get_center(self):
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    def get_width(self):
        return self.max_x - self.min_x

    def get_height(self):
        return self.max_y - self.min_y


class PriorityZone:
    """Зона повышенного интереса"""
    def __init__(self, center_x, center_y, radius, priority=1):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.priority = priority

    def contains(self, x, y):
        dist = ((x - self.center_x) ** 2 + (y - self.center_y) ** 2) ** 0.5
        return dist <= self.radius


class AdaptiveBoundarySearch:
    def __init__(self, drone, boundary, sensor_range_m, speed_pct, depth_m,
                 priority_zones=None, battery_threshold=20, return_home=True,
                 cube_found_callback=None):
        self.drone = drone
        self.boundary = boundary
        self.sensor_range = sensor_range_m      # дальность датчика/сонара (м)
        self.speed = speed_pct
        self.depth = depth_m
        self.priority_zones = priority_zones or []
        self.battery_threshold = battery_threshold
        self.return_home = return_home
        self.cube_found_callback = cube_found_callback or (lambda: False)
        
        # Адаптивный шаг между линиями (перекрытие 20%)
        self.line_spacing = sensor_range_m * 1.6
        
        # Текущая позиция (оценка через дед 레кoning)
        self.current_x, self.current_y = boundary.get_center()
        self.current_heading = 0
        self.survey_lines = []
        self.current_line = 0
        self.direction = 1  # 1 = forward, -1 = backward
        self.home_position = boundary.get_center()
        self.battery_level = 100
        self.cube_found = False

    def simulate_battery_drain(self):
        self.battery_level -= 0.05
        return self.battery_level

    def check_battery(self):
        if self.battery_level <= self.battery_threshold:
            print(f"[AdaptiveSearch] НИЗКИЙ ЗАРЯД: {self.battery_level:.0f}%! Возврат на базу.")
            return True
        return False

    def check_cube_found(self):
        """Проверка флага находки кубика"""
        if self.cube_found_callback():
            self.cube_found = True
            print("[AdaptiveSearch] >>> КУБИК НАЙДЕН! Остановка поиска <<<")
            return True
        return False

    def check_boundaries(self, x, y):
        if not self.boundary.contains(x, y):
            safe_x = max(self.boundary.min_x + 1, min(x, self.boundary.max_x - 1))
            safe_y = max(self.boundary.min_y + 1, min(y, self.boundary.max_y - 1))
            print(f"[AdaptiveSearch] ГРАНИЦА! Коррекция: ({x:.1f},{y:.1f}) -> ({safe_x:.1f},{safe_y:.1f})")
            return safe_x, safe_y, True
        return x, y, False

    def calculate_priority_weight(self, x, y):
        weight = 1.0
        for zone in self.priority_zones:
            if zone.contains(x, y):
                weight *= zone.priority
        return weight

    def generate_survey_lines(self):
        """Генерация линий обследования с учетом приоритетов"""
        center_x, center_y = self.boundary.get_center()
        width = self.boundary.get_width()
        height = self.boundary.get_height()

        if width >= height:
            # Линии параллельно Y (вдоль высоты)
            num_lines = int(width / self.line_spacing) + 1
            start_x = self.boundary.min_x + (width - (num_lines - 1) * self.line_spacing) / 2

            for i in range(num_lines):
                x = start_x + i * self.line_spacing
                weight = self.calculate_priority_weight(x, center_y)
                self.survey_lines.append({
                    'x': x,
                    'y_start': self.boundary.min_y + 1,
                    'y_end': self.boundary.max_y - 1,
                    'priority_weight': weight
                })
        else:
            # Линии параллельно X (вдоль ширины)
            num_lines = int(height / self.line_spacing) + 1
            start_y = self.boundary.min_y + (height - (num_lines - 1) * self.line_spacing) / 2

            for i in range(num_lines):
                y = start_y + i * self.line_spacing
                weight = self.calculate_priority_weight(center_x, y)
                self.survey_lines.append({
                    'y': y,
                    'x_start': self.boundary.min_x + 1,
                    'x_end': self.boundary.max_x - 1,
                    'priority_weight': weight
                })

        # Сортировка по приоритету (сначала важные)
        self.survey_lines.sort(key=lambda L: -L['priority_weight'])
        print(f"[AdaptiveSearch] Сгенерировано {len(self.survey_lines)} линий, шаг {self.line_spacing:.1f}м")

    def dive(self):
        print(f"[AdaptiveSearch] Ныряем на {self.depth}м...")
        self.drone.set_depth(self.depth)
        time.sleep(3)

    def rise(self):
        print("[AdaptiveSearch] Всплываем...")
        self.drone.set_depth(0)
        time.sleep(2)

    def move_to(self, target_x, target_y, tolerance=0.5):
        """Перемещение к точке (упрощенная навигация через время)"""
        distance = ((target_x - self.current_x) ** 2 + (target_y - self.current_y) ** 2) ** 0.5
        if distance < tolerance:
            return True
            
        # Ориентируемся к цели
        import math
        target_heading = math.degrees(math.atan2(target_y - self.current_y, target_x - self.current_x))
        # Нормализуем
        while target_heading < 0: target_heading += 360
        while target_heading >= 360: target_heading -= 360
        
        self.drone.set_course(int(target_heading))
        time.sleep(2)
        
        # Движемся
        est_speed_ms = max(self.speed * 0.01, 0.2)
        move_time = distance / est_speed_ms
        
        self.drone.set_speed(self.speed)
        time.sleep(move_time)
        self.drone.set_speed(0)
        
        self.current_x, self.current_y = target_x, target_y
        self.simulate_battery_drain()
        return True

    def turn_180(self):
        """Разворот на 180° на месте (как в rotation.py)"""
        print("[AdaptiveSearch] Разворот 180°...")
        self.drone.set_speed(0)
        time.sleep(0.5)
        
        angle = 0
        step = 3
        while angle < 180:
            self.drone.change_course(step)
            time.sleep(0.05)
            angle += step
        
        time.sleep(1)

    def run_search(self):
        """Основной цикл адаптивного поиска"""
        self.dive()
        self.generate_survey_lines()

        print(f"\n[AdaptiveSearch] === НАЧАЛО ПОИСКА ===")
        print(f"  Границы: X[{self.boundary.min_x}:{self.boundary.max_x}], Y[{self.boundary.min_y}:{self.boundary.max_y}]")
        print(f"  Датчик: {self.sensor_range}м, Скорость: {self.speed}%, Глубина: {self.depth}м")
        print(f"  База: {self.home_position}")

        # К стартовой точке первой линии
        if self.survey_lines:
            first = self.survey_lines[0]
            sx = first.get('x', first.get('x_start', self.current_x))
            sy = first.get('y_start', first.get('y', self.current_y))
            self.move_to(sx, sy)

        for i, line in enumerate(self.survey_lines):
            # Проверки перед каждой линией
            if self.check_battery():
                self.return_to_home()
                break
            if self.check_cube_found():
                break

            print(f"\n[AdaptiveSearch] --- Линия {i+1}/{len(self.survey_lines)} (приоритет: {line['priority_weight']:.1f}) ---")

            if 'x' in line:  # Вертикальные линии
                x = line['x']
                y_start = line['y_start']
                y_end = line['y_end']
                target_y = y_end if self.direction > 0 else y_start
                self.move_to(x, target_y)
            else:  # Горизонтальные линии
                y = line['y']
                x_start = line['x_start']
                x_end = line['x_end']
                target_x = x_end if self.direction > 0 else x_start
                self.move_to(target_x, y)

            # Проверка границ
            self.current_x, self.current_y, boundary_hit = self.check_boundaries(self.current_x, self.current_y)
            if boundary_hit and self.return_home:
                print("[AdaptiveSearch] Упёрлись в стенку! Возврат на базу.")
                self.return_to_home()
                break

            # Контроль глубины
            depth_cm = self.drone.get_depth()
            print(f"[AdaptiveSearch] Глубина: {depth_cm/100:.2f}м (цель: {self.depth}м)")

            # Проверка кубика в конце линии
            if self.check_cube_found():
                break

            # Разворот для следующей линии
            if i < len(self.survey_lines) - 1:
                self.turn_180()
                self.direction *= -1
                time.sleep(0.5)

        self.drone.set_speed(0)
        self.rise()
        print(f"\n[AdaptiveSearch] === ПОИСК ЗАВЕРШЕН ===")
        print(f"  Кубик найден: {self.cube_found}")
        print(f"  Остаток заряда: {self.battery_level:.0f}%")

    def return_to_home(self):
        print(f"[AdaptiveSearch] Возврат на базу: {self.home_position}")
        self.move_to(self.home_position[0], self.home_position[1])


def cube_found_simulation():
    """Симуляция детектора кубика - замените на реальный"""
    # Здесь должна быть ваша логика обнаружения (лазер, камера, сонар)
    # Верните True когда кубик найден
    return False


def main():
    # === ПАРАМЕТРЫ МИССИИ ===
    BOUNDARY = Boundary(min_x=0, max_x=10, min_y=0, max_y=8)  # Бассейн 10x8 м
    SENSOR_RANGE = 1.5      # метры (лазер/сонар)
    SPEED = 50              # %
    DEPTH = 2               # метры
    
    # Приоритетные зоны (например, предполагаемое место кубика)
    PRIORITY_ZONES = [
        PriorityZone(center_x=5, center_y=4, radius=1.5, priority=3.0),  # центр
        PriorityZone(center_x=2, center_y=2, radius=1.0, priority=2.0),  # угол
    ]

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    search = AdaptiveBoundarySearch(
        drone=drone,
        boundary=BOUNDARY,
        sensor_range=SENSOR_RANGE,
        speed=SPEED,
        depth=DEPTH,
        priority_zones=PRIORITY_ZONES,
        battery_threshold=20,
        return_home=True,
        cube_found_callback=cube_found_simulation
    )

    search.run_search()

    drone.stop()
    print("[AdaptiveSearch] Миссия завершена")


if __name__ == "__main__":
    main()