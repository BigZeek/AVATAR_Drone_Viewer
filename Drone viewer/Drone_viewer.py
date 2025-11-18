import sys
import os
import math #Unused Imports Added For Later Implementations
import datetime
from PySide6.QtCore import QObject, QUrl, Qt, Signal, QSize, Property, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor, QVector3D, QPixmap, QQuaternion, QMatrix4x4
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QGridLayout, QTextEdit, QPushButton
)
from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender


class ModelEntity(Qt3DCore.QEntity):
    def __init__(self, parent=None, model_path="Drone viewer\drone.obj"):
        super().__init__(parent)

        # Material
        self.material = Qt3DExtras.QPhongMaterial(self)
        self.material.setDiffuse(QColor(150, 180, 220))

        # Mesh
        if model_path and os.path.exists(model_path):
            self.mesh = Qt3DRender.QMesh()
            self.mesh.setSource(QUrl.fromLocalFile(model_path))
        else:
            self.mesh = Qt3DExtras.QCuboidMesh()  # Fallback

        # Transform
        self.transform = Qt3DCore.QTransform()
        self._rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), -90)  # 45° Y-axis rotation
        self.transform.setRotation(self._rotation)

        # Components
        self.addComponent(self.mesh)
        self.addComponent(self.material)
        self.addComponent(self.transform)

    def setRotation(self, rotation: QQuaternion):
        self._rotation = rotation
        self.transform.setRotation(rotation)

    def getRotation(self) -> QQuaternion:
        return self._rotation
    
    def applyRotation(self, axis: QVector3D, angle: float):
        rot = QQuaternion.fromAxisAndAngle(axis, angle)
        self._rotation = rot * self._rotation
        self.transform.setPosition(self._rotation)

    def setPosition(self, position: QVector3D):
        """Move the drone model in 3D space."""
        if not isinstance(position, QVector3D):
            raise TypeError(f"Expected QVector3D, got {type(position).name}")
        self.transform.setTranslation(position)

    rotation = Property(QQuaternion, getRotation, setPosition)


class ObjectViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Viewer")
        self.resize(800, 600)

        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # Create 3D Window
        self.view = Qt3DExtras.Qt3DWindow()
        self.container = self.createWindowContainer(self.view)
        main_layout.addWidget(self.container, 1)

        # Root Entity
        self.rootEntity = Qt3DCore.QEntity()

        # Camera
        self.camera = self.view.camera()
        self.camera.lens().setPerspectiveProjection(45.0, 16/9, 0.1, 1400)
        self.camera.setPosition(QVector3D(10, 0, 120))
        self.camera.setViewCenter(QVector3D(10, 0, 0))

        # Light
        lightEntity = Qt3DCore.QEntity(self.rootEntity)
        light = Qt3DRender.QPointLight(lightEntity)
        light.setColor("grey")
        light.setIntensity(1)
        lightTransform = Qt3DCore.QTransform()
        lightTransform.setTranslation(QVector3D(10, 10, 10))
        lightEntity.addComponent(light)
        lightEntity.addComponent(lightTransform)


        # .OBJ File Opener
        model_path = os.path.join(os.path.dirname(__file__))  # OLD Replace with your path
        
        self.drone = ModelEntity(self.rootEntity, model_path=model_path)
        self.frame_entities = []
        frames_folder = os.path.join(os.path.dirname(__file__), "frames")
        if os.path.isdir(frames_folder):
            obj_files = sorted([
                os.path.join(frames_folder, f)
                for f in os.listdir(frames_folder)
                if f.endswith(".obj")
            ])
            for path in obj_files:
                entity = ModelEntity(self.rootEntity, model_path=path)
                entity.setEnabled(False)  # Hide initially
                self.frame_entities.append(entity)

        if self.frame_entities:
            self.frame_entities[0].setEnabled(True)  # Show first frame



        # Set root object of the scene
        self.view.setRootEntity(self.rootEntity)

        # Animation
        self.animation = QPropertyAnimation(self.drone, b"rotation")
        self.animation.setDuration(500)

        # Controls
        control_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)

        # Control Buttons
        self.addButton("Rotate Left", lambda: self.rotate_all("left"), control_layout)
        self.addButton("Rotate Right", lambda: self.rotate_all("right"), control_layout)
        self.addButton("Rotate Up", lambda: self.rotate_all("up"), control_layout)
        self.addButton("Rotate Down", lambda: self.rotate_all("down"), control_layout)
        self.addButton("Zoom Out", self.zoom_out, control_layout)
        self.addButton("Zoom In", self.zoom_in, control_layout)
        self.addButton("Takeoff", self.takeoff, control_layout)
        self.addButton("Land", self.land, control_layout)

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.next_obj_frame)

        self.obj_frames = []  # List of paths to .obj files
        self.current_frame_index = 0

        # Load .obj frame paths (change folder and naming if needed)
        frames_folder = os.path.join(os.path.dirname(__file__), "frames")
        if os.path.isdir(frames_folder):
            self.obj_frames = sorted([
                os.path.join(frames_folder, f)
                for f in os.listdir(frames_folder)
                if f.endswith(".obj")
            ])



        control_layout.addStretch()
        
    def zoom_out(self):
        cam_pos = self.camera.position()
        view_center = self.camera.viewCenter()
        direction = cam_pos - view_center
        new_pos = cam_pos + direction.normalized() * 5.0  # Adjust zoom speed here
        self.camera.setPosition(new_pos)

    def zoom_in(self):
        cam_pos = self.camera.position()
        view_center = self.camera.viewCenter()
        direction = cam_pos - view_center
        zoom_step = 5.0  # Adjust for faster/slower zoom
        new_pos = cam_pos - direction.normalized() * zoom_step
        self.camera.setPosition(new_pos)

    def addButton(self, label, callback, layout):
        btn = QPushButton(label)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

    #Controls drone degrees of rotation per button press
    def rotate_drone(self, direction):
        current = self.drone.getRotation()
        axis = QVector3D(0, 1, 0)
        angle = 10
        
        if direction == "left":
            axis = QVector3D(0, 1, 0)
            angle = 10
        elif direction == "right":
            axis = QVector3D(0, 1, 0)
            angle = -10
        elif direction == "up":
            axis = QVector3D(1, 0, 0)
            angle = 10
        elif direction == "down":
            axis = QVector3D(1, 0, 0)
            angle = -10

        rot = QQuaternion.fromAxisAndAngle(axis, angle)
        new_rotation = rot * current

        self.animation.stop()
        self.animation.setStartValue(current)
        self.animation.setEndValue(new_rotation)
        self.animation.start()


    #Start animation
    def play_obj_animation(self):
        if not self.obj_frames:
            print("No .obj frames found.")
            return

        self.current_frame_index = 0
        self.animation_timer.start(33)  # milliseconds per frame [33 = ~30 FPS (1000ms / 30)]
    
    #Stop animation
    def stop_obj_animation(self):
        if not self.obj_frames:
            print("No .obj frames found.")
            return

        
        self.animation_timer.stop()


    def takeoff(self):
        self.controller.takeoff()
        self.play_obj_animation()
        
    def land(self):
        self.controller.land()
        self.stop_obj_animation()
        
        
    #Frame Buffering to stop studdering
    def next_obj_frame(self):
        if not self.frame_entities:
            return

        # Hide current frame
        self.frame_entities[self.current_frame_index].setEnabled(False)

        # Advance index
        self.current_frame_index = (self.current_frame_index + 1) % len(self.frame_entities)

        # Show next frame
        self.frame_entities[self.current_frame_index].setEnabled(True)

    def rotate_animation_frames(self, direction):
        axis = QVector3D(0, 1, 0)
        angle = 10

        if direction == "left":
            axis = QVector3D(0, 1, 0)
            angle = 10
        elif direction == "right":
            axis = QVector3D(0, 1, 0)
            angle = -10
        elif direction == "up":
            axis = QVector3D(1, 0, 0)
            angle = 10
        elif direction == "down":
            axis = QVector3D(1, 0, 0)
            angle = -10

        for entity in self.frame_entities:
            entity.applyRotation(axis, angle)

    def rotate_all(self, direction):
        self.rotate_drone(direction)
        self.rotate_animation_frames(direction)
        
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ObjectViewer()
    viewer.show()
    sys.exit(app.exec())
