import cv2
from pioneer_sdk import Pioneer

class ArucoDetector:
    """
    Детектор ArUco маркеров.

    Система координат дрона (body-fixed):
        Центр — геометрический центр дрона.
        Ось X — вправо (относительно носа).
        Ось Y — вперёд (по направлению полёта).
        Ось Z — вверх (в небо).
    """

    def __init__(self, dictionary_type=cv2.aruco.DICT_4X4_100):
        """
        Инициализация детектора ArUco маркеров.
        
        Args:
            dictionary_type: Тип словаря ArUco маркеров (по умолчанию DICT_4X4_100)
        """
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
        self.aruco_params = cv2.aruco.DetectorParameters()

        # self.aruco_params.errorCorrectionRate = 0.7
        self.aruco_params.minMarkerPerimeterRate = 0.1

        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        self.image_size = (640, 480)
        self.ground_cover = (4.4, 3.4)   # надо пофиксить потому что зависит от высоты полета
    

    def detect_markers_presence(self, frame, visual=False):
        """
        Определяет наличие ArUco маркеров на изображении.
        
        Args:
            frame: Входное изображение
            visual: Режим визуализации
            
        Returns:
            bool: True если маркеры обнаружены, False в противном случае
        """

        corners, ids, _ = self.detector.detectMarkers(frame)
        
        if ids is not None:  
            if visual: 
                frame_copy = frame.copy()
                cv2.aruco.drawDetectedMarkers(frame_copy, corners, ids)
                cv2.imshow("DetectedMarkers", frame_copy)
                cv2.waitKey(1)

            return True
        
        elif visual:
            cv2.imshow("DetectedMarkers", frame)
            cv2.waitKey(1)

        return False 
    
    
    def get_markers_image_coordinates(self, frame):
        """
        Находит координаты центров ArUco маркеров на изображении.
        
        Args:
            frame: Входное изображение
            
        Returns:
            dict: {marker_id: (center_x, center_y)} или пустой словарь
        """
        markers = {}
        corners, ids, _ = self.detector.detectMarkers(frame)
        
        if ids is not None:
            for i in range(len(ids)):
                marker_id = ids[i][0]
                marker_corners = corners[i][0]
                center_x = int(marker_corners[:, 0].mean())
                center_y = int(marker_corners[:, 1].mean())
                markers[marker_id] = (center_x, center_y)
        
        return markers
    

    def get_markers_global_positions(self, frame, pioneer: Pioneer, verbose=False):
        """
        Получает глобальные координаты всех обнаруженных ArUco маркеров.
        
        Args:
            frame: Входное изображение
            pioneer: Объект для получения позиции дрона
            verbose: Режим подробного вывода
            
        Returns:
            dict: {marker_id: (global_x, global_y)} или None если маркеры не найдены
        """
        
        global_markers = {}
        
        if not self.detect_markers_presence(frame):
            if verbose:
                print("Маркеры не обнаружены")
            return None
        
        image_markers = self.get_markers_image_coordinates(frame)
        drone_pos = pioneer.get_local_position_lps(get_last_received=True)
        drone_x, drone_y = drone_pos[:2]
        
        img_width, img_height = self.image_size
        ground_width, ground_height = self.ground_cover
        scale_x = ground_width / img_width
        scale_y = ground_height / img_height
        img_center_x = img_width / 2
        img_center_y = img_height / 2
        
        for marker_id, (marker_x, marker_y) in image_markers.items():
            global_x = drone_x + (marker_x - img_center_x) * scale_x
            global_y = drone_y - (marker_y - img_center_y) * scale_y
            global_markers[marker_id] = (global_x, global_y)

        if verbose and global_markers:
            for marker_id, coords in global_markers.items():
                print(f"Маркер {marker_id}: {coords}")

        return global_markers



    def get_markers_relative_positions(self, frame,  pioneer: Pioneer, verbose=False):
        """
        Получает координаты маркеров относительно дрона в системе координат дрона.

        Система координат дрона:
            X — вправо (относительно носа)
            Y — вперёд (по направлению полёта)
            Z — вверх (в небо)

        Маркер на земле будет иметь отрицательный Z (ниже дрона).

        Args:
            frame: Входное изображение
            verbose: Режим подробного вывода

        Returns:
            dict: {marker_id: (rel_x, rel_y, rel_z)} или None если маркеры не найдены
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None or len(ids) == 0:
            if verbose:
                print("Маркеры не обнаружены")
            return None

        img_width, img_height = self.image_size
        ground_width, ground_height = self.ground_cover
        scale_x = ground_width / img_width
        scale_y = ground_height / img_height


        img_center_x = img_width / 2
        img_center_y = img_height / 2

        drone_x, drone_y, drone_z  = pioneer.get_local_position_lps(get_last_received=True)
      

        rel_markers = {}
        for i in range(len(ids)):
            marker_id = int(ids[i][0])
            
            obj_center_x = int(corners[i][0][:, 0].mean())
            obj_center_y = int(corners[i][0][:, 1].mean())
            
            # смещение в пикселях по модулю
            dx_px = abs(obj_center_x - img_center_x)
            dy_px = abs(obj_center_y - img_center_y)
            
            # в метры
            dx_m = dx_px * scale_x
            dy_m = dy_px * scale_y
            
            if obj_center_x > img_center_x:
                dx_m = -dx_m
            
            if obj_center_y > img_center_y:
                dy_m = +dy_m
            else:
                dy_m = -dy_m
            
        
            dz_m = -drone_z

        
            rel_markers[marker_id] = (round(dx_m, 3), round(dy_m, 3), round(dz_m, 3))

        if verbose and rel_markers:
            for marker_id, coords in rel_markers.items():
                print(f"Маркер {marker_id}: x={coords[0]}m y={coords[1]}m z={coords[2]}m")

        return rel_markers














    def get_marker_offset_to_drone(self, frame, pioneer):
        """
        Получает смещение до маркера в глобальных координатах,
        считая координаты дрона за (0, 0, height).

        Система координат дрона:
            X — вправо (относительно носа)
            Y — вперед (по направлению полёта)
            Z — вверх (в небо)

        Args:
            frame: Входное изображение
            pioneer: Объект Pioneer для получения позиции дрона

        Returns:
            list: [{marker_id, global_x, global_y, rel_x, rel_y, rel_z}, ...]
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None or len(ids) == 0:
            return []

        drone_pos = pioneer.get_local_position_lps(get_last_received=True)
        drone_x, drone_y, drone_z = drone_pos[0], drone_pos[1], drone_pos[2]

        img_width, img_height = self.image_size
        ground_width, ground_height = self.ground_cover
        scale_x = ground_width / img_width
        scale_y = ground_height / img_height


        img_center_x = img_width / 2 
        img_center_y = img_height / 2
        print(img_center_x, img_center_y)

        
        results = []
        for i in range(len(ids)):
            marker_id = int(ids[i][0])
            cx = int(corners[i][0][:, 0].mean())
            cy = int(corners[i][0][:, 1].mean())

            offset_x = (cx - img_center_x) * scale_x
            offset_y = (img_center_y - cy) * scale_y

            global_x = drone_x + offset_x
            global_y = drone_y + offset_y

            rel_x = offset_x
            rel_y = offset_y
            rel_z = -drone_z

            results.append({
                'marker_id': marker_id,
                'global_x': round(global_x, 3),
                'global_y': round(global_y, 3),
                'rel_x': round(rel_x, 3),
                'rel_y': round(rel_y, 3),
                'rel_z': round(rel_z, 3),
            })

        return results



    def get_detected_markers_ids(self, frame):
        """
        Возвращает список ID всех обнаруженных маркеров на кадре.
        
        Args:
            frame: Входное изображение
            
        Returns:
            list: Список ID маркеров или пустой список, если маркеры не найдены
        """
        
        _, ids, _ = self.detector.detectMarkers(frame)
        return ids.flatten().tolist() if ids is not None else []
    