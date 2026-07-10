import cv2
import numpy as np
from pioneer_sdk import Pioneer, Camera

class CameraCalibrator:
    def __init__(self):
        # Начальные приближения параметров камеры
        self.camera_matrix = np.array([
            [700.0, 0.0, 320.0],
            [0.0, 700.0, 240.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        
        self.dist_coeffs = np.array([0.1, -0.05, 0.001, 0.001, 0.0], dtype=np.float32)
        self.learning_rate = 0.01
        self.target_position = np.array([0, 0, 2.0], dtype=np.float32)
        self.min_error_pair = [float('inf'), float('inf')]
        self.calibration_complete = False  # Флаг завершения калибровки
        self.precision_threshold = 1e-3  # Порог точности (0.00001)

    def update_parameters(self, tvecs):
        """Адаптивная корректировка параметров камеры"""
        if self.calibration_complete:
            return
            
        error = tvecs.flatten() - self.target_position
        current_abs_errors = np.abs(error[:2])
        
        # Проверяем достижение требуемой точности
        if all(abs_err < self.precision_threshold for abs_err in current_abs_errors):
            self.calibration_complete = True
            self.min_error_pair = error[:2].copy()
            print(f"Достигнута требуемая точность! Ошибки: X={error[0]:.8f}, Y={error[1]:.8f}")
            return
            
        # Обновляем минимальные ошибки
        both_improved = (current_abs_errors[0] < abs(self.min_error_pair[0]) and 
                        current_abs_errors[1] < abs(self.min_error_pair[1]))
        
        if both_improved:
            self.min_error_pair = error[:2].copy()
            print(f"Новые минимальные ошибки: X={error[0]:.8f}, Y={error[1]:.8f}")
        
        # Корректировка параметров камеры
        self.camera_matrix[0, 0] *= (1 - self.learning_rate * error[0])
        self.camera_matrix[1, 1] *= (1 - self.learning_rate * error[1])
        self.camera_matrix[0, 2] += self.learning_rate * error[0] * 100
        self.camera_matrix[1, 2] += self.learning_rate * error[1] * 100
        self.dist_coeffs[0] += self.learning_rate * error[2] * 0.1
        self.dist_coeffs[1] += self.learning_rate * error[0] * 0.1

# Инициализация
pioneer = Pioneer(name="pioneer", ip="127.0.0.1", mavlink_port=8000, 
                 connection_method="udpout", device="dev/serial0", 
                 baud=115200, logger=True, log_connection=True)

camera = Camera(ip="127.0.0.1", port=18000, log_connection=True, timeout=4)
calibrator = CameraCalibrator()

# Параметры маркера
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
aruco_params = cv2.aruco.DetectorParameters()
aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
size_of_marker = 0.1

points_of_marker = np.array([
    [size_of_marker/2, -size_of_marker/2, 0],
    [-size_of_marker/2, -size_of_marker/2, 0],
    [-size_of_marker/2, size_of_marker/2, 0],
    [size_of_marker/2, size_of_marker/2, 0]
], dtype=np.float32)

# Полет к начальной позиции
flight_height = 2.0
pioneer.arm()
pioneer.takeoff()


pioneer.go_to_local_point(x=0, y=0, z=flight_height, yaw=0)

print("Начало калибровки. Цель: ошибки < 0.00001 по X и Y")



try:
    while True:
        if calibrator.calibration_complete:
            print("Калибровка успешно завершена!")
            break
        
            
    
        byte_frame = camera.get_frame()


        
        if byte_frame is not None:
            frame = cv2.imdecode(np.frombuffer(byte_frame, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            # Поиск маркеров
            corners, ids, rejected = aruco_detector.detectMarkers(frame)
            
            if ids is not None and len(ids) > 0:
                success, rvecs, tvecs = cv2.solvePnP(
                    points_of_marker, corners[0], 
                    calibrator.camera_matrix, calibrator.dist_coeffs
                )
                
                if success:
                    current_tvecs = tvecs.flatten()
                    # print(f"Current tvecs: [{current_tvecs[0]:.8f}, {current_tvecs[1]:.8f}, {current_tvecs[2]:.8f}]")
                    
                    # Адаптивная калибровка
                    calibrator.update_parameters(tvecs)
                    
                    # Визуализация
                    # cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                    # cv2.drawFrameAxes(frame, calibrator.camera_matrix, 
                    #                 calibrator.dist_coeffs, rvecs, tvecs, 0.1)
            
            cv2.imshow("Camera Calibration", frame)
        
        key = cv2.waitKey(1)
        if key == ord('q'):
            break

finally:
    # Сохранение результатов и завершение
    print("\nИтоговые результаты:")
    print(f"Минимальные ошибки: X={calibrator.min_error_pair[0]:.8f}, Y={calibrator.min_error_pair[1]:.8f}")
    
    cv_file = cv2.FileStorage("optimized_camera_params.yml", cv2.FILE_STORAGE_WRITE)
    cv_file.write("mtx", calibrator.camera_matrix)
    cv_file.write("dist", calibrator.dist_coeffs)
    cv_file.release()
    
    cv2.destroyAllWindows()
    pioneer.land()
    pioneer.close_connection()
    print("Параметры камеры сохранены в optimized_camera_params.yml")