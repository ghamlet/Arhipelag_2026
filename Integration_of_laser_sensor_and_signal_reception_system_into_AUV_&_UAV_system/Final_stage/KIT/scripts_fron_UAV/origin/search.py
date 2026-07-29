from user.library import DroneLibrary
import time


def search_and_identify_objects(drone):
    for _ in range(5):
        move_to_next_zone(drone)
        objects_found = scan_bottom()
        identified_objects = identify_objects(objects_found)
        process_identified_objects(identified_objects)


def move_to_next_zone(drone):
    drone.set_course(180)
    time.sleep(3)


def scan_bottom():
    return ['камень', 'дерево', 'металлический объект']


def identify_objects(objects_found):
    identified_objects = {}
    for obj in objects_found:
        if obj == 'камень':
            identified_objects[obj] = 'обычный камень'
        elif obj == 'дерево':
            identified_objects[obj] = 'древесный обломок'
        elif obj == 'металлический объект':
            identified_objects[obj] = 'металлический отход'
        else:
            identified_objects[obj] = 'неизвестный объект'
    return identified_objects


def process_identified_objects(identified_objects):
    for obj, desc in identified_objects.items():
        print(f"Найден предмет: {obj}, идентифицирован как: {desc}")


if __name__ == "__main__":
    drone = DroneLibrary()
    drone.start()

    search_and_identify_objects(drone)

    drone.stop()
