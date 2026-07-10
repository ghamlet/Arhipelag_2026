class FlightMissionRunner:
    def __init__(self, points=None, start_x=-4, start_y=4, field_size=10, drone_cover=2):
        """Инициализация миссии с параметрами поля и обзора дрона"""
        self.start_x = start_x
        self.start_y = start_y
        self.field_size = field_size
        self.drone_cover = drone_cover
        self.is_complete_var = False

        self.points = points if points else self._generate_flight_path()
        self.current_index = 0
    

    def _generate_flight_path(self):
        """Генерирует маршрут 'змейкой' с учётом параметров поля"""
        step = self.drone_cover
        half_field = self.field_size // 2
        points = []
        y = self.start_y
        
        for row in range(int(self.field_size / self.drone_cover)):
            if row % 2 == 0:
                x_range = range(-half_field + 1, half_field, step)
            else:
                x_range = range(half_field - 1, -half_field, -step)
            
            for x in x_range:
                points.append((x, y))
            
            y -= step  
        
        return points

    
    def has_more_points(self):
        """Проверяет, остались ли точки для посещения"""
        if self.current_index < len(self.points):
            return True
        else:
            self.is_complete_var = True
            return False
        
    
    def get_next_point(self):
        """
        Возвращает следующую точку маршрута
        Returns:
            tuple|None: (x, y) или None если маршрут завершён
        """
        if self.has_more_points():
            point = self.points[self.current_index]
            self.current_index += 1
            return point 
        
        return None
    
    
    def get_total_points(self):
        """Возвращает общее количество точек в маршруте"""
        return len(self.points)
    
    def get_current_progress(self):
        """Возвращает прогресс выполнения миссии в процентах"""
        return (self.current_index / len(self.points)) * 100 if self.points else 0
    

    def is_complete(self):
        return self.is_complete_var
