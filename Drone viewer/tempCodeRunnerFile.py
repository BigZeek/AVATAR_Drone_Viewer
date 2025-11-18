import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QQuaternion
from djitellopy import Tello
from Drone_viewer import ObjectViewer
class TelloController(QThread):
    telemetry_updated = Signal(float, float, float)  # yaw, pitch, roll
    def __init__(self):
        super().__init__()
        self.tello = Tello()
        self.running = True

    def run(self):
        self.tello.connect()
        self.tello.streamon()
        while self.running:
            try:
                yaw = self.tello.get_yaw()
                pitch = self.tello.get_pitch()
                roll = self.tello.get_roll()
                self.telemetry_updated.emit(yaw, pitch, roll)
            except Exception as e:
                print("Telemetry error:", e)
            self.msleep(100)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class DroneViewer(ObjectViewer):
    def __init__(self):
        super().__init__()
        self.controller = TelloController()
        self.controller.telemetry_updated.connect(self.update_rotation)
        self.controller.start()

    def update_rotation(self, yaw, pitch, roll):
        rotation = QQuaternion.fromEulerAngles(pitch, yaw, roll)
        self.drone.setRotation(rotation)

    def rotate_drone(self, direction):
        super().rotate_drone(direction)
        try:
            if direction == "left":
                self.controller.tello.rotate_counter_clockwise(10)
            elif direction == "right":
                self.controller.tello.rotate_clockwise(10)
            elif direction == "up":
                self.controller.tello.move_up(20)
            elif direction == "down":
                self.controller.tello.move_down(20)
        except Exception as e:
            print("Drone command error:", e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = DroneViewer()
    viewer.show()
    sys.exit(app.exec())