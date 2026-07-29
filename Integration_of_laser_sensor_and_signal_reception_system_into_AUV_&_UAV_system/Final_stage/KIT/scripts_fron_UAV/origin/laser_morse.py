#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import time
from user.library import DroneLibrary


def main():
    # Инициализация библиотеки
    drone = DroneLibrary()

    # Переводим дрон в автономный режим
    drone.start()

    try:

        # Убеждаемся, что лазер выключен   
        rospy.loginfo('Turning laser off')
        drone.set_laser(0)

        # Посылаем точку
        rospy.loginfo('Sending dot via laser beam')
        drone.set_laser(1)
        time.sleep(1)
        drone.set_laser(0)

        # Посылаем тире
        rospy.loginfo('Sending dash via laser beam')
        drone.set_laser(1)
        time.sleep(3)
        drone.set_laser(0)

        # Возвращаем управление джойстику и прекращаем работу с библиотекой
        drone.set_offline_mode()
        drone.stop()

    except Exception as e:
        rospy.logerr(f'Error: {e}')
        drone.stop()
        raise


if __name__ == '__main__':
    main()
