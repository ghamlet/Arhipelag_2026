import math
from pioneer_sdk import Pioneer
from typing import Dict, List, Tuple



class FlightMissionPathPlanner :
    def __init__(self, all_avg_coords: Dict[int, Tuple[float, float]], pioneer_instance: Pioneer, verbose=False):
        """
        Инициализация планировщика полета.
        
        Параметры:
            all_avg_coords: словарь {marker_id: (x, y)} с координатами маркеров
            pioneer: экземпляр класса Pioneer (опционально)
            start_position: начальная позиция дрона (если None, получаем от дрона)
        """
        self.all_avg_coords = all_avg_coords
        self.pioneer = pioneer_instance
        # self.start_position = self._get_current_position_drone()
        self.marker_graph = self._build_marker_graph()
        # self._flight_plan = self._generate_flight_plan() 
        self.verbose = verbose
    

    def _get_current_position_drone(self):
        """Получает текущую позицию дрона через класс Pioneer."""
        return self.pioneer.get_local_position_lps(get_last_received=True)[:2]
    

    def _build_marker_graph(self):
        """Строит граф переходов между маркерами на основе их ID."""
        graph = {}
        for marker_id in self.all_avg_coords:
            first_digit = marker_id // 10  
            second_digit = marker_id % 10  
            graph[first_digit] = second_digit
        return graph
    
    def _find_closest_marker(self, position):
        """Находит маркер, ближайший к указанной позиции."""
        closest_id = None
        min_distance = float('inf')
        
        for marker_id, coords in self.all_avg_coords.items():
            distance = math.dist(position, coords)
            if distance < min_distance:
                min_distance = distance
                closest_id = marker_id
        return closest_id
    


    def _generate_flight_plan(self):
        """Генерирует план полёта по маркерам (вызывается автоматически при инициализации)."""
        current_position = self._get_current_position_drone()
        visited = set()
        flight_plan = []
        
        current_marker_id = self._find_closest_marker(current_position)
        flight_plan.append(current_marker_id)
        visited.add(current_marker_id // 10)  
        
        while True:
            current_node = current_marker_id // 10
            next_node = self.marker_graph.get(current_node)
            
            if next_node is None or next_node in visited:
                break
                
            next_marker_candidates = [
                marker_id for marker_id in self.all_avg_coords 
                if marker_id // 10 == next_node and marker_id not in visited
            ]
            
            if not next_marker_candidates:
                break
                
            next_marker_id = next_marker_candidates[0]
            flight_plan.append(next_marker_id)
            visited.add(next_node)
            current_marker_id = next_marker_id
            
        return flight_plan
    
    def get_flight_plan(self):
        """Возвращает сгенерированный план полёта (ID маркеров)."""
        return self._flight_plan
    

    def get_coordinates_plan(self, flight_plan=None, verbose=False):
        """
        Возвращает план полёта в виде координат.
        
        Параметры:
            flight_plan: если None, используется сохранённый план
        """
        if flight_plan is None:
            flight_plan = self._flight_plan

        coordinates_plan = [self.all_avg_coords[marker_id] for marker_id in flight_plan]
        if verbose:
            print(coordinates_plan)

        return coordinates_plan
    

    def calculate_all_routes_distances(self) -> Dict[Tuple[int], float]:
        """
        Рассчитывает длины всех возможных маршрутов по логике графа маркеров.
        
        Returns:
            Словарь {последовательность_маркеров: общая_дистанция}
        """
        routes_distances = {}
        current_position = self._get_current_position_drone()
        
        # Находим все возможные стартовые маркеры (ближайшие к каждой начальной точке)
        start_markers = set()
        for first_node in self.marker_graph.keys():
            closest = None
            min_dist = float('inf')
            for marker_id, coords in self.all_avg_coords.items():
                if marker_id // 10 == first_node:
                    dist = math.dist(current_position, coords)
                    if dist < min_dist:
                        min_dist = dist
                        closest = marker_id
            if closest is not None:
                start_markers.add(closest)
        
        # Генерируем все возможные маршруты
        for start_marker in start_markers:
            visited = set()
            route = []
            current_marker = start_marker
            route.append(current_marker)
            visited.add(current_marker // 10)
            
            while True:
                current_node = current_marker // 10
                next_node = self.marker_graph.get(current_node)
                
                if next_node is None or next_node in visited:
                    break
                    
                next_marker_candidates = [
                    marker_id for marker_id in self.all_avg_coords 
                    if marker_id // 10 == next_node and marker_id not in visited
                ]
                
                if not next_marker_candidates:
                    break
                    
                next_marker = next_marker_candidates[0]
                route.append(next_marker)
                visited.add(next_node)
                current_marker = next_marker
            
            # Рассчитываем общую дистанцию маршрута
            total_distance = 0.0
            prev_point = current_position
            
            for marker_id in route:
                marker_point = self.all_avg_coords[marker_id]
                total_distance += math.dist(prev_point, marker_point)
                prev_point = marker_point
            
            routes_distances[tuple(route)] = total_distance
        
        return routes_distances
    

    
    def find_optimal_route(self) -> Tuple[List[int], float]:
        """
        Находит оптимальный маршрут (с минимальной дистанцией).
        
        Returns:
            Кортеж (маршрут, дистанция)
        """
        routes_distances = self.calculate_all_routes_distances()
        
        if not routes_distances:
            return [], 0.0
        
        optimal_route, min_distance = min(
            routes_distances.items(),
            key=lambda item: item[1]
        )
        
        if self.verbose:
            # Выводим все маршруты и их дистанции
            print("Все возможные маршруты и их дистанции:")
            for route, distance in routes_distances.items():
                print(f"Маршрут: {route}, Дистанция: {distance:.2f} м")
            
            print(f"\nОптимальный маршрут: {optimal_route}, Минимальная дистанция: {min_distance:.2f} м")
            
        return list(optimal_route), min_distance
