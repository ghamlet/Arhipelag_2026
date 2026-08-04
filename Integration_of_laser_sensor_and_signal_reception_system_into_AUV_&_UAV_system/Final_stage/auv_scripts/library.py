import rospy
import actionlib
import threading
import time
import message_filters
from drone_lib.static_methods import constrain

from drone.msg import DepthAction, DepthGoal
from drone.msg import PitchAction, PitchGoal
from drone.msg import RollAction, RollGoal
from drone.msg import SpeedAction, SpeedGoal
from drone.msg import CourseAction, CourseGoal
from drone.msg import EnableControlAction, EnableControlGoal

from drone.msg import LightAction, LightGoal
from drone.msg import HandAction, HandGoal
from drone.msg import LaserAction, LaserGoal
from drone.msg import PayloadAction, PayloadGoal

from drone.msg import Depth, Pose


class DroneLibrary:
    """
    Класс DroneLibrary представляет собой библиотеку для управления дроном.
    """

    def __init__(self):
        """
        Инициализирует объект класса DroneLibrary.

        Поля класса:
            running (bool): Флаг, указывающий на состояние выполнения дроном.
            started (bool): Флаг, указывающий на то, был ли запущен дрон.
            set_depth_client: Клиент для установки глубины дрона.
            set_pitch_client: Клиент для установки угла тангажа дрона.
            set_roll_client: Клиент для установки угла крена дрона.
            set_speed_client: Клиент для установки скорости дрона.
            set_course_client: Клиент для установки курса дрона.
            change_depth_client: Клиент для изменения глубины дрона.
            change_pitch_client: Клиент для изменения угла тангажа дрона.
            change_roll_client: Клиент для изменения угла крена дрона.
            change_speed_client: Клиент для изменения скорости дрона.
            change_course_client: Клиент для изменения курса дрона.
            hand_client: Клиент для управления рукой дрона.
            headlight_client: Клиент для управления освещением дрона.
            laser_client: Клиент для управления лазером в буе или на самом дроне.
            payload_client: Клиент для управления полезной нагрузкой на дроне.
            control_client: Клиент для управления режимом управления дроном.
        """

        self.running = threading.Event()
        self.started = threading.Event()

        rospy.init_node('drone_library_node')

        self.depth = 0
        self.pitch = 0
        self.roll = 0
        self.yaw = 0

        self.set_depth_client = actionlib.SimpleActionClient('actions/set_depth', DepthAction)
        self.set_pitch_client = actionlib.SimpleActionClient('actions/set_pitch', PitchAction)
        self.set_roll_client = actionlib.SimpleActionClient('actions/set_roll', RollAction)
        self.set_speed_client = actionlib.SimpleActionClient('actions/set_speed', SpeedAction)
        self.set_course_client = actionlib.SimpleActionClient('actions/set_course', CourseAction)

        self.change_depth_client = actionlib.SimpleActionClient('actions/change_depth', DepthAction)
        self.change_pitch_client = actionlib.SimpleActionClient('actions/change_pitch', PitchAction)
        self.change_roll_client = actionlib.SimpleActionClient('actions/change_roll', RollAction)
        self.change_speed_client = actionlib.SimpleActionClient('actions/change_speed', SpeedAction)
        self.change_course_client = actionlib.SimpleActionClient('actions/change_course', CourseAction)

        self.enable_control_client = actionlib.SimpleActionClient('actions/enable_control', EnableControlAction)

        self.set_light_client = actionlib.SimpleActionClient('actions/light_control', LightAction)
        self.set_hand_client = actionlib.SimpleActionClient('actions/hand_control', HandAction)
        self.set_laser_client = actionlib.SimpleActionClient('actions/laser_control', LaserAction)
        self.set_payload_client = actionlib.SimpleActionClient('actions/payload_control', PayloadAction)

        # Подписка на сообщения от датчика ориентации
        euler_subscriber = message_filters.Subscriber('sensor/euler', Pose)
        self.tseuler = message_filters.TimeSynchronizer([euler_subscriber], 1)
        self.tseuler.registerCallback(self.euler_callback)

        # Подписка на сообщения от датчика глубины
        depth_subscriber = message_filters.Subscriber('sensor/depth', Depth)
        self.tsdepth = message_filters.TimeSynchronizer([depth_subscriber], 1)
        self.tsdepth.registerCallback(self.depth_callback)

    def depth_callback(self, depth_msg):
        """
        Коллбек для получения сообщений от датчика глубины.

        Args:
            None

        Returns:
            None
        """
        self.depth = depth_msg.value
        rospy.logdebug(f'DEPTH {self.depth}')

    def euler_callback(self, pose_msg):
        """
        Коллбек для получения сообщений от датчика ориентации.

        Args:
            None

        Returns:
            None
        """
        self.pitch = pose_msg.pitch
        self.roll = pose_msg.roll
        self.yaw = pose_msg.yaw
        rospy.logdebug(f'EULER pitch: {self.pitch}, roll: {self.roll}, yaw: {self.yaw}')

    def get_depth(self):
        """
        Метод для получения текущей глубины.

        Args:
            None

        Returns:
            Значение глубины в условных единицах
        """
        return int(self.depth)

    def get_course(self):
        """
        Метод для получения текущего курса.

        Args:
            None

        Returns:
            Значение текущего курса в градусах
        """
        return int(self.yaw)

    def get_roll(self):
        return int(self.roll)

    def get_pitch(self):
        return int(self.pitch)

    def change_course(self, angle):
        """
        Метод для изменения курса дрона.

        Args:
            angle: На какой угол надо изменить текущий курс/ориентацию дрона.

        Returns:
            None
        """
        rospy.loginfo(f'change_course({angle})')
        goal = CourseGoal()
        goal.target = angle
        self.change_course_client.send_goal(goal)
        self.change_course_client.wait_for_result()

    def change_depth(self, depth):
        """
        Метод для смены глубины дрона.

        Args:
            depth: Насколько изменить глубину дрона.

        Returns:
            None
        """
        rospy.loginfo(f'change_depth({depth})')
        goal = DepthGoal()
        goal.target = depth
        self.change_depth_client.send_goal(goal)
        self.change_depth_client.wait_for_result()

    def change_roll(self, roll):
        """
        Метод для изменения угла крена дрона.

        Args:
            roll: Значение для изменения угла крена дрона.

        Returns:
            None
        """
        rospy.loginfo(f'change_roll({roll})')
        goal = RollGoal()
        goal.target = roll
        self.change_roll_client.send_goal(goal)
        self.change_roll_client.wait_for_result()

    def change_pitch(self, pitch):
        """
        Метод для изменения угла тангажа дрона.

        Args:
            pitch: Значение для изменения угла тангажа дрона.

        Returns:
            None
        """
        rospy.loginfo(f'change_pitch({pitch})')
        goal = PitchGoal()
        goal.target = pitch
        self.change_pitch_client.send_goal(goal)
        self.change_pitch_client.wait_for_result()

    def change_speed(self, speed):
        """
        Метод для изменения скорости дрона.

        Args:
            speed: Значение для изменения скорости дрона.

        Returns:
            None
        """
        rospy.loginfo(f'change_speed({speed})')
        goal = SpeedGoal()
        goal.target = speed
        self.change_speed_client.send_goal(goal)
        self.change_speed_client.wait_for_result()

    def set_course(self, angle):
        """
        Метод для установки курса дрона.

        Args:
            angle: Какой курс установить (относительно начального курса).

        Returns:
            None
        """
        rospy.loginfo(f'set_course({angle})')
        goal = CourseGoal()
        goal.target = angle
        self.set_course_client.send_goal(goal)
        self.set_course_client.wait_for_result()

    def set_depth(self, depth):
        """
        Метод для смены глубины дрона.

        Args:
            depth: Значение для установки глубины дрона.

        Returns:
            None
        """
        rospy.loginfo(f'set_depth({depth})')
        goal = DepthGoal()
        goal.target = depth
        self.set_depth_client.send_goal(goal)
        self.set_depth_client.wait_for_result()

    def set_roll(self, roll):
        """
        Метод для установки угла крена дрона.

        Args:
            roll: Значение для установки угла крена дрона.

        Returns:
            None
        """
        rospy.loginfo(f'set_roll({roll})')
        goal = RollGoal()
        goal.target = roll
        self.set_roll_client.send_goal(goal)
        self.set_roll_client.wait_for_result()

    def set_pitch(self, pitch):
        """
        Метод для установки угла тангажа дрона.

        Args:
            pitch: Значение для установки угла тангажа дрона.

        Returns:
            None
        """
        rospy.loginfo(f'set_pitch({pitch})')
        goal = PitchGoal()
        goal.target = pitch
        self.set_pitch_client.send_goal(goal)
        self.set_pitch_client.wait_for_result()

    def set_speed(self, speed):
        """
        Метод для установки скорости дрона.

        Args:
            speed: Значение для установки скорости дрона.

        Returns:
            None
        """
        val = constrain(speed, 100, -100)
        rospy.loginfo(f'set_speed({speed})')
        goal = SpeedGoal()
        goal.target = int(-val)
        self.set_speed_client.send_goal(goal)
        self.set_speed_client.wait_for_result()

    def set_headlight(self, value):
        """
        Метод для управления фонарем на дроне.

        Args:
            value: Значение для управления фонарем.

        Returns:
            None
        """
        val = constrain(value, 100, 0)
        rospy.loginfo(f'set_headlight({value})')
        goal = LightGoal()
        goal.target = int(val * 255 / 100)
        self.set_light_client.send_goal(goal)
        self.set_light_client.wait_for_result()

    def set_hand(self, value):
        """
        Метод для управления рукой дрона.

        Args:
            value: Значение для управления рукой.

        Returns:
            None
        """
        rospy.loginfo(f'set_hand({value})')
        goal = HandGoal()
        goal.target = value
        self.set_hand_client.send_goal(goal)
        self.set_hand_client.wait_for_result()

    def set_laser(self, value):
        """
        Метод для управления лазером в буе или на дроне.

        Args:
            value: Значение для управления лазером (0 выключает, 1 включает луч).

        Returns:
            None
        """
        rospy.loginfo(f'set_laser({value})')
        goal = LaserGoal()
        goal.target = value
        self.set_laser_client.send_goal(goal)
        self.set_laser_client.wait_for_result()

    def set_payload(self, value):
        """
        Метод для управления полезной нагрузкой на дроне.

        Args:
            value: Значение для управления полезной нагрузкой.

        Returns:
            None
        """
        rospy.loginfo(f'set_payload({value})')
        goal = PayloadGoal()
        goal.target = value
        self.set_payload_client.send_goal(goal)
        self.set_payload_client.wait_for_result()

    def set_online_mode(self):
        """
        Метод для возврата управления через джойстик.
        Синоним для set_control(False).

        Args:
            None

        Returns:
            None
        """
        self.set_control(0)

    def set_offline_mode(self):
        """
        Метод для входа в режим автономного управления.
        Синоним для set_control(True).

        Args:
            None

        Returns:
            None
        """
        self.set_control(1)

    def set_control(self, state):
        """
        Метод для перехвата контроля.

        Args:
            state: 1, если перехватываем управление, 0 - если управление через джойстик.

        Returns:
            None
        """
        rospy.loginfo(f'set_control({state})')
        goal = EnableControlGoal()
        goal.target = state
        self.enable_control_client.send_goal(goal)
        self.enable_control_client.wait_for_result()

    def stop(self):
        """
        Прекращение автономной работы с дроном.

        Args:
            None

        Returns:
            None
        """
        if self.running:
            rospy.loginfo('stop()')
            self.set_control(False)
            self.running.clear()
            self.thread.join()

    def start(self, takecontrol=True):
        """
        Начало автономной работы с дроном.

        Args:
            None

        Returns:
            None
        """
        if (not self.running.is_set()):
            rospy.loginfo('start()')
            self.started.clear()
            self.running.set()
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

            # Ждём...
            while (not self.started.is_set()):
                time.sleep(0.1)

            if takecontrol:
                self.set_control(True)

            self.started.clear()
            time.sleep(3)
            rospy.loginfo('Начинается выполнение программы')

    def run(self):
        """
        Метод для выполнения основной логики управления дроном.

        В данном методе инициализируется частота обновления и ожидаются все необходимые серверы ROS,
        необходимые для отправки команд управления дроном.

        Args:
            None

        Returns:
            None
        """
        rate = rospy.Rate(100)

        self.set_depth_client.wait_for_server()
        rospy.logdebug('set_depth_client is available')
        self.set_pitch_client.wait_for_server()
        rospy.logdebug('set_pitch_client is available')
        self.set_roll_client.wait_for_server()
        rospy.logdebug('set_roll_client is available')
        self.set_speed_client.wait_for_server()
        rospy.logdebug('set_speed_client is available')
        self.set_course_client.wait_for_server()
        rospy.logdebug('set_course_client is available')
        self.change_depth_client.wait_for_server()
        rospy.logdebug('change_depth_client is available')
        self.change_pitch_client.wait_for_server()
        rospy.logdebug('change_pitch_client is available')
        self.change_roll_client.wait_for_server()
        rospy.logdebug('change_roll_client is available')
        self.change_speed_client.wait_for_server()
        rospy.logdebug('change_speed_client is available')
        self.change_course_client.wait_for_server()
        rospy.logdebug('change_course_client is available')

        self.enable_control_client.wait_for_server()
        rospy.logdebug('enable_control_client is available')
        self.set_light_client.wait_for_server()
        rospy.logdebug('set_light_client is available')
        self.set_hand_client.wait_for_server()
        rospy.logdebug('set_hand_client is available')
        self.set_laser_client.wait_for_server()
        rospy.logdebug('set_laser_client is available')
        self.set_payload_client.wait_for_server()
        rospy.logdebug('set_payload_client is available')

        self.started.set()
        rospy.loginfo('All servers are available')

        while (not rospy.is_shutdown() and self.running.is_set()):
            rate.sleep()
