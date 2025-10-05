from djitellopy import Tello
# from GUI5_ManualDroneControl.py import DroneController

# Assumes drone already connected 

class DroneFeedback():
    
    def __init__(self):
        super().__init__()
    
    # Function returns drone pitch, yaw, roll for viewer
    def get_drone_attitude():
        while True: # Run continuously while program is active
            pitch = Tello.get_pitch()
            roll = Tello.get_roll()
            yaw = Tello.get_yaw()
        # Send to Drone_viewer script
        
    
### Add future feedback below (video stream, speed, etc) ###