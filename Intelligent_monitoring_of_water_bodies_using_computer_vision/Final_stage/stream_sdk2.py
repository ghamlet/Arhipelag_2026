import cv2
from pioneer_sdk2 import Camera, CameraType,ImageViewer


def main():
    camera = Camera(camera_type=CameraType.MAIN)
    viewer = ImageViewer()


    try:
        while True:
            frame = camera.get_cv_frame(timeout=5.0)
            if frame is not None:
                cv2.imshow("Drone Stream (SDK2)", frame)
                viewer.imshow("camera", frame, fps=30)

            

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
