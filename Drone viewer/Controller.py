import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QQuaternion, QVector3D
from djitellopy import Tello
from Drone_viewer import ObjectViewer


class TelloController(QThread):
    telemetry_updated = Signal(float, float, float, float, float, float)  # yaw, pitch, roll, x, y, z

    def __init__(self):
        super().__init__()
        self.tello = Tello()
        self.running = True
        self.last_time = None
        self.position = QVector3D(0.0, 0.0, 0.0)  # Estimated position (meters)

    def run(self):
        self.tello.connect()
        self.tello.streamon()
        print(f"Tello connected — Battery: {self.tello.get_battery()}%")

        self.last_time = time.time()

        while self.running:
            try:
                # --- Orientation ---
                yaw = self.tello.get_yaw()
                pitch = self.tello.get_pitch()
                roll = self.tello.get_roll()

                # --- Velocity data ---
                vx = self.tello.get_speed_x() / 100.0  # convert cm/s → m/s
                vy = self.tello.get_speed_y() / 100.0
                vz = self.tello.get_speed_z() / 100.0

                # --- Integrate velocity to approximate position ---
                current_time = time.time()
                dt = current_time - self.last_time
                self.last_time = current_time

                # Integrate velocity (basic motion estimation)
                self.position.setX(self.position.x() + vx * dt)
                self.position.setY(self.position.y() + vy * dt)
                self.position.setZ(self.position.z() + vz * dt)

                # Emit all telemetry
                self.telemetry_updated.emit(yaw, pitch, roll,
                                            self.position.x(),
                                            self.position.y(),
                                            self.position.z())

            except Exception as e:
                print("Telemetry error:", e)

            self.msleep(100)  # update rate ~10 Hz

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class DroneViewer(ObjectViewer):
    def __init__(self):
        super().__init__()

        self.controller = TelloController()
        self.controller.telemetry_updated.connect(self.update_pose)
        self.controller.start()

        self.gyro_sync_enabled = True

    def update_pose(self, yaw, pitch, roll, x, y, z):
        """
        Update the 3D drone model’s rotation and XYZ position in real time.
        """
        if not self.gyro_sync_enabled:
            return

        # --- Rotation ---
        rotation = QQuaternion.fromEulerAngles(pitch, yaw, roll)
        self.drone.transform.setRotation(rotation)

        # --- Position ---
        position = QVector3D(x, y, z)
        self.drone.setPosition(position)

    def takeoff(self):
        self.controller.tello.takeoff()
        
    def land(self):
        self.controller.tello.land()
    
    def rotate_drone(self, direction):
        """
        Manual drone movement controls. The viewer’s position updates automatically.
        """
        try:
            if direction == "left":
                self.controller.tello.rotate_counter_clockwise(10)
            elif direction == "right":
                self.controller.tello.rotate_clockwise(10)
            elif direction == "up":
                self.controller.tello.move_up(20)
            elif direction == "down":
                self.controller.tello.move_down(20)
            elif direction == "forward":
                self.controller.tello.move_forward(20)
            elif direction == "back":
                self.controller.tello.move_back(20)
        except Exception as e:
            print("Drone command error:", e)

    def closeEvent(self, event):
        self.controller.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = DroneViewer()
    viewer.show()
    sys.exit(app.exec())
