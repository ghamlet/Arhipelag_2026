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
    while not drone.point_reached():           # ждем, пока дрон не достигнет заданной точки
        show_camera()                          # показываем видео с камеры во время полета
        time.sleep(0.1)                        # ставим небольшую паузу, чтобы не нагружать программу


def go_to_start_point():                       # функция взлета и выхода в начальную точку
    drone.arm()                                # включаем двигатели
    drone.takeoff()                            # производим взлет
    time.sleep(3)  # обязательно чтоб успел взлететь

    drone.go_to_local_point(x=0, y=0, z=1, yaw=0, time=3) # летим в начальную точку
                                                          # x, y, z - координаты точки в метрах
    time.sleep(3)  # обязательно чтоб успел взлететь

                                                          # yaw - поворот по курсу в градусах
                                                          # time - время, за которое нужно достигнуть точку

    wait_for_point()                           # ждем, пока дрон долетит до начальной точки


def fly_through_points(points):                # функция полета по заданным точкам
    for point in points:                       # перебираем все точки из списка
        drone.go_to_local_point(               # отправляем дрон в текущую точку
            x=point["x"],                      # координата точки по оси X
            y=point["y"],                      # координата точки по оси Y
            z=point["z"],                      # координата точки по оси Z
            yaw=point["yaw"],                  # поворот по курсу в градусах
            time=3                             # время, за которое нужно достигнуть точку
        )

        wait_for_point()                       # ждем, пока дрон долетит до текущей точки


ALTITUDE = 1.5  # фиксированная высота полета (метры)

waypoints = [
    "140; 175",
    "240; 175",
    "340; 175",
    "340; 275",
    "240; 275",
    "140; 275",
]

def parse_waypoints(raw):
    result = []
    for w in raw:
        x, y = w.split(";")
        result.append({"x": float(x.strip()), "y": float(y.strip()), "z": ALTITUDE, "yaw": 0})
    return result



try:                                           # основной код находится внутри блока try
    go_to_start_point()                        # выполняем взлет и выход в начальную точку
    fly_through_points(parse_waypoints(waypoints))  # выполняем полет по заданным точкам
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