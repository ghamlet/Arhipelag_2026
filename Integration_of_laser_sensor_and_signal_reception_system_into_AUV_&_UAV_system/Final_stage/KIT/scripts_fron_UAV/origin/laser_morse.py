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
        while not rospy.is_shutdown():
            try:
                interval = 0.5
                # Убеждаемся, что лазер выключен   
                rospy.loginfo('Turning laser off')
                drone.set_laser(0)

                # Лазер горит 2 секунды
                rospy.loginfo('Laser on for 2 seconds')
                drone.set_laser(1)
                time.sleep(4)
                drone.set_laser(0)

                # Лазер выключен на 0.5 секунды
                rospy.loginfo('Laser off for 0.5 seconds')
                drone.set_laser(0)
                time.sleep(interval)

                # Равные промежутки горения и выключения
                rospy.loginfo('Laser on for 0.5 seconds')
                drone.set_laser(1)
                time.sleep(interval)
                drone.set_laser(0)

                rospy.loginfo('Laser off for 0.5 seconds')
                drone.set_laser(0)
                time.sleep(interval)

                rospy.loginfo('Laser on for 0.5 seconds')
                drone.set_laser(1)
                time.sleep(interval)
                drone.set_laser(0)

              

            except rospy.ROSInterruptException:
                # Прерывание по Ctrl+C
                print('Interrupted by user (Ctrl+C)')
                break
                
    except KeyboardInterrupt:
        # Альтернативный способ перехвата Ctrl+C
        print('Keyboard interrupt received')
        
    except Exception as e:
        rospy.logerr(f'Error: {e}')
        
    finally:
        # Гарантированно выключаем лазер и останавливаем дрон
        rospy.loginfo('Stopping drone and turning off laser...')
        drone.set_laser(0)
        drone.stop()
        rospy.loginfo('Drone stopped successfully')


if __name__ == '__main__':
    main()