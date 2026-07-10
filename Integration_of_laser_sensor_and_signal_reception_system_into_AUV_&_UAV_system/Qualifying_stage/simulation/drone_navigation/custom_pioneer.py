import time
from pioneer_sdk import Pioneer


class CustomPioneer(Pioneer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover_start_time = None
        self._hover_duration = 0
        self._target_position = None  
        self._reached_flag = False   


    def go_to_local_point(self, x, y, z, yaw=0):
        """Переопределенный метод движения к точке с запоминанием цели"""
        self._target_position = (x, y, z)
        self._reached_flag = False
        super().go_to_local_point(x, y, z, yaw)
        


    def start_hover(self, duration):
        """Начинает процесс зависания на указанное время"""
        if not self.is_hovering():
            self._hover_start_time = time.time()
            self._hover_duration = duration
            # print(f"[Pioneer] Начато зависание на {duration} сек")


    def is_hovering(self):
        """Проверяет, выполняется ли зависание"""
        return self._hover_start_time is not None


    def check_hover_complete(self):
        """Проверяет завершение зависания и возвращает True по его окончании"""
        if not self.is_hovering():
            return False
            
        if time.time() - self._hover_start_time >= self._hover_duration:
            self._hover_start_time = None
            # print("[Pioneer] Зависание завершено")
            return True
            
        return False
    


   
    def point_reached_by_faster_mode(self, threshold=0.1):
        """
        Проверяет достижение текущей цели (однократное срабатывание)
        
        Args:
            check_only_x: проверять только по оси X
            check_only_y: проверять только по оси Y
            
        Returns:
            bool: True если цель достигнута (срабатывает один раз)
        """
        if self._target_position is None or self._reached_flag:
            return False
            
        target_x, target_y, _ = self._target_position
        cur_x, cur_y = self.get_local_position_lps(get_last_received=True)[:2]
        
        x_reached = (abs(cur_x - target_x) < threshold)
        y_reached = (abs(cur_y - target_y) < threshold)
        
        
        reached = x_reached and y_reached
        
        if reached:
            self._reached_flag = True
            return True
            
        return False