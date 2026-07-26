from pioneer_sdk2 import Pioneer, Camera, ImageViewer # импортируем классы из библиотеки pioneer_sdk2
import time                                    # библиотека time содержит функции для работы со временем

drone = Pioneer()                              # создаем экземпляр класса Pioneer, устанавливаем соединение
camera = Camera()                              # создаем экземпляр класса Camera для получения кадров с камеры
viewer = ImageViewer()                         # создаем экземпляр класса ImageViewer для трансляции видео

def show_camera():                             # функция вывода видео с камеры дрона
    frame = camera.get_cv_frame(timeout=1.0)   # получаем один кадр с камеры
                                               # timeout=1.0 - время ожидания кадра в секундах

    if frame is not None:                      # проверяем, что изображение получено
        viewer.imshow("pioneer_camera", frame) # отправляем изображение в RTSP-трансляцию




def wait_for_point():                          # функция ожидания прилета дрона в точку
    while not drone.point_reached():   
                # ждем, пока дрон не достигнет заданной точки
       # show_camera()                          # показываем видео с камеры во время полета
        time.sleep(0.1)                        # ставим небольшую паузу, чтобы не нагружать программу


def go_to_start_point():                       # функция взлета и выхода в начальную точку
    drone.arm()   
    time.sleep(3)                         # включаем двигатели
    drone.takeoff()                            # производим взлет
    time.sleep(3)  # обязательно чтоб успел взлететь

    drone.go_to_local_point(x=0, y=0, z=1.7, yaw=0, time=5) # летим в начальную точку

    wait_for_point()                           # ждем, пока дрон долетит до начальной точки


def hover(seconds: float):                     # функция зависания на текущей точке
    end_time = time.time() + seconds          # вычисляем время окончания
    while time.time() < end_time:             # ждем указанное время
        show_camera()                         # показываем видео во время зависания
        time.sleep(0.1)                       # пауза чтобы не нагружать процессор


def fly_through_points(points):                # функция полета по заданным точкам
    for point in points:                       # перебираем все точки из списка
        drone.go_to_local_point(               # отправляем дрон в текущую точку
            x=point["x"],                      # координата точки по оси X
            y=point["y"],                      # координата точки по оси Y
            z=point["z"]   ,
            yaw=0 ,
            time=5                  # координата точки по оси Z
                                         # время, за которое нужно достигнуть точку
        )

        wait_for_point()                       # ждем, пока дрон долетит до текущей точки
        hover(10)


ALTITUDE = 1.8  # фиксированная высота полета (метры)

# waypoints = [
#     (1.40, 1.75),
#     (2.40, 1.75),
#     (3.40, 1.75),
#     (3.40, 2.75),
#     (2.40, 2.75),
#     (1.40, 2.75)

# ]

waypoints = [
(-2.9, 0),
(-2.9, 1.3),
(-2.9, 2.0),
(-2.9, 2.8),
(-2.9, 3.5),
(-2.2, 3.5),
(-2.2, 2.8),
(-2.2, 2.0),
(-2.2, 1.3),
(-1.6, 1.3),
(-1.6, 2.0),
(-1.6, 2.8),
(-1.6, 3.5)

]


def parse_waypoints(raw):
    result = []
    for x, y in raw:
        result.append({"x": x, "y": y, "z": ALTITUDE, "yaw": 0})
    return result



try:                                           # основной код находится внутри блока try
    go_to_start_point()                        # выполняем взлет и выход в начальную точку
    fly_through_points(parse_waypoints(waypoints))  # выполняем полет по заданным точкам


    drone.go_to_local_point(               # отправляем дрон в текущую точку
                x=0,                      # координата точки по оси X
                y=0,                      # координата точки по оси Y
                z=ALTITUDE,
                yaw=0                  # координата точки по оси Z
                                             # время, за которое нужно достигнуть точку
            )
    
    wait_for_point()  


    
    drone.land()                               # производим посадку после завершения полета

except KeyboardInterrupt:                      # если пользователь остановил программу сочетанием Ctrl+C
    print("Остановка программы, производится посадка") # выводим сообщение об остановке программы
    drone.land()                                       # сажаем дрон

except Exception as error:                     # если произошла другая ошибка
    print("Ошибка:", error)                    # выводим текст ошибки
    drone.land()                               # сажаем дрон при ошибке

finally:                                       # блок finally выполнится в любом случае
    viewer.close()                             # останавливаем RTSP-трансляцию
    camera.stop()                              # останавливаем получение кадров с камеры
    drone.close_connection()                   # закрываем соединение с квадрокоптером