import cv2
import numpy as np
import os,sys
import time as t
from pymycobot import MyCobot280
import RPi.GPIO as GPIO

# THIS SCIRPT IS MADE BY CHATGPT

class cube_picker():
    def __init__(self):
        self.mc = MyCobot280(os.popen("ls /dev/ttyAMA*").readline()[:-1], 1000000)
        self.mc.send_angles([0.61, 45.87, -92.37, -41.3, 2.02, 9.58], 20)
        t.sleep(2.5)
        self.GPIO = GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(20, GPIO.OUT)
        GPIO.setup(21, GPIO.OUT)
        GPIO.output(20, 1)
        GPIO.output(21, 1)

        self.move_angles = [
            [0.61, 45.87, -92.37, -41.3, 2.02, 9.58],  # init the point
            [18.8, -7.91, -54.49, -23.02, -0.79, -14.76],  # point to grab
        ]

        self.move_coords = [
            [132.2, -136.9, 200.8, -178.24, -3.72, -107.17],  # D Sorting area
            [238.8, -124.1, 204.3, -169.69, -5.52, -96.52], # C Sorting area
            [115.8, 177.3, 210.6, 178.06, -0.92, -6.11], # A Sorting area
            [-6.9, 173.2, 201.5, 179.93, 0.63, 33.83], # B Sorting area
        ]

        # These ranges were found using hsv_calibration.py. It is a script made by ChatGPT.
        self.HSV = {
            "blue": [np.array([96, 122, 139]), np.array([132, 255, 255])],
            "green": [np.array([77, 69, 64]), np.array([91, 255, 255])],
            "yellow": [np.array([22, 100, 100]), np.array([30, 255, 255])],
            "red": [np.array([0, 107, 149]), np.array([8, 255, 255])],
        }

        self.old_HSV = {
            "blue": [np.array([100, 43, 46]), np.array([124, 255, 255])],
            "green": [np.array([35, 43, 35]), np.array([90, 255, 255])],
            "yellow": [np.array([11, 85, 70]), np.array([59, 255, 245])],
            "red": [np.array([0, 43, 46]), np.array([8, 255, 255])],
        }

        # Colors of the cubes in RGB color space
        self.colors = {
            "blue": [160, 133, 56],
            "green": [106, 144, 41],
            "yellow": [91, 196, 204],
            "red": [82, 100, 197],
        }

        # ArUco Parameters
        self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
        self.aruco_params = cv2.aruco.DetectorParameters_create()

        #ArUco Centers (pixel and real) REAL CALIBRATED FOR SLIGHT SLACK IN ROBOT
        self.aruco1_center = None
        self.aruco2_center = None
        
        self.real_aruco1_center = (235,-30)
        self.real_aruco2_center = (120,86)

        # Center points used for cropping the frame
        self.aruco_centers = []
        self.c1X = self.c1Y = self.c2X = self.c2Y = 0

        self.c_x = self.c_y = 0
        
        # Camera position
        self.camera_x = 155
        self.camera_y = 15

    def color_detect_cubes(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        cubes_detected = []
        centers = []
        for color, item in self.HSV.items():
            rgb = self.colors[color]
            lower = item[0]
            upper = item[1]

            mask = cv2.inRange(hsv, lower, upper)

            ret, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)      

            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for c in contours:
                area = cv2.contourArea(c)
                if area > 10000:
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(img, (x,y), (x+w, y+h), rgb, 2)
                    cx, cy = (x+int(w/2), y+int(h/2))
                    cv2.circle(img, (cx, cy), 3, (255,255,255), -1)
                    cubes_detected.append(color)
                    centers.append([cx,cy])
        
        return cubes_detected, centers

    def detect_aruco(self,img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        corners, ids, rejectImaPoint = cv2.aruco.detectMarkers(
            gray, self.aruco_dict, parameters=self.aruco_params
        )

        centers = []

        for corner in corners:
            pts = corner[0]

            cX = int(pts[:, 0].mean())
            cY = int(pts[:, 1].mean())

            centers.append([cX, cY])

        self.aruco_centers.append(centers)
    
    def set_centers(self):
        #centers = np.array(self.aruco_centers)
        x1_sum = []
        x2_sum = []
        y1_sum = []
        y2_sum = []
        for center in self.aruco_centers:
            try:
                x1, y1 = center[0]
                x2, y2 = center[1]

                x1_sum.append(x1)
                x2_sum.append(x2)
                y1_sum.append(y1)
                y2_sum.append(y2)
            except:
                pass
        
        self.set_params(
                (sum(x1_sum)+sum(x2_sum))/20.0,
                (sum(y1_sum)+sum(y2_sum))/20.0,
                abs(sum(x1_sum)-sum(x2_sum))/10.0 +
                abs(sum(y1_sum)-sum(y2_sum))/10.0
            )

        self.c1X = int(np.mean(np.array(x1_sum))) - 28
        self.c1Y = int(np.mean(np.array(y1_sum))) + 28

        self.c2X = int(np.mean(np.array(x2_sum))) + 28
        self.c2Y = int(np.mean(np.array(y2_sum))) - 28

        self.aruco_centers = []
    
    def crop_frame(self,frame):
        #cv2.circle(frame, (self.c1X, self.c1Y), 4, (0, 0, 255), -1)
        #cv2.circle(frame, (self.c2X, self.c2Y), 4, (0, 0, 255), -1)

        x_min, x_max = sorted([self.c1X, self.c2X])
        y_min, y_max = sorted([self.c1Y, self.c2Y])

        cropped = frame[y_min:y_max, x_min:x_max]

        fx = 1.5
        fy = 1.5
        cropped = cv2.resize(cropped, (0, 0), fx=fx, fy=fy,
                           interpolation=cv2.INTER_CUBIC)
        return cropped
    
    def get_position(self, x, y):
        return ((y - self.c_y)*self.ratio + self.camera_x), ((x - self.c_x)*self.ratio + self.camera_y)
    
    def set_params(self, c_x, c_y, ratio):
        self.c_x = c_x
        self.c_y = c_y

    def gpio_status(self, flag):
        if flag:
            self.GPIO.output(20, 0)
            self.GPIO.output(21, 0)
        else:
            self.GPIO.output(20, 1)
            self.GPIO.output(21, 1)
    
    def set_aruco(self):
        x1_sum = []
        x2_sum = []
        y1_sum = []
        y2_sum = []
        for center in self.aruco_centers:
            try:
                x1, y1 = center[0]
                x2, y2 = center[1]

                x1_sum.append(x1)
                x2_sum.append(x2)
                y1_sum.append(y1)
                y2_sum.append(y2)
            except:
                pass

        self.aruco1_center = (int(np.mean(np.array(x1_sum))), int(np.mean(np.array(y1_sum))))
        self.aruco2_center = (int(np.mean(np.array(x2_sum))), int(np.mean(np.array(y2_sum))))

        self.aruco_centers = []

        self.estimate_similarity()

    def estimate_similarity(self):
        image_pts = np.asarray([self.aruco1_center, self.aruco2_center], dtype=np.float32)
        robot_xy  = np.asarray([self.real_aruco1_center, self.real_aruco2_center],  dtype=np.float32)

        M, inliers = cv2.estimateAffinePartial2D(image_pts, robot_xy, method=cv2.LMEDS)
        self.M = M

    def pixel_to_robot_xy(self,x,y):
        pt = np.array([x, y, 1.0], dtype=np.float32)
        X, Y = (self.M @ pt)

        return float(X), float(Y) 
    
    def grasp(self,x,y):
        # Moving to general grab point
        self.mc.send_angles(self.move_angles[1], 25)
        t.sleep(3)

        # Moving to approach point
        self.mc.send_coords([x, y,  170.6, 179.87, -3.78, -62.75], 25, 1)
        t.sleep(3)

        # Moving to actual grab point
        self.mc.send_coords([x, y, 103, 179.87, -3.78, -62.75], 25, 0)
        t.sleep(3)

        # Moving to approach point
        self.mc.send_coords([x, y,  170.6, 179.87, -3.78, -62.75], 25, 1)
        t.sleep(3)

        # Moving to general grab point
        self.mc.send_angles(self.move_angles[1], 25)
        t.sleep(3)

        # Moving to idle point
        self.mc.send_angles(self.move_angles[0], 25)




        

# open the camera
print("Starting init!")
cap_num = 0
cap = cv2.VideoCapture(cap_num)

if not cap.isOpened():
    cap.open()

picker = cube_picker()

# Init parameters
init = True
init_frame = 0

# Calibration Parameters
calibrate = True
calibrate_frame = 0

# Detection parameters
detected_frame = 1

key = None
while (key!=27):    
    _, frame = cap.read()
    
    if init:
        picker.detect_aruco(frame)
        if init_frame > 10:
            picker.set_centers()
            print("Init done! Starting Calibration")
            init = False
        init_frame += 1
        
    elif calibrate:
        frame = picker.crop_frame(frame)
        picker.detect_aruco(frame)
        if calibrate_frame > 50:
            print("Calibration done!\n")
            picker.set_aruco()
            calibrate_frame = 0
            calibrate = False
        calibrate_frame += 1

    else:
        frame = picker.crop_frame(frame)

        cubes_detected, centers = picker.color_detect_cubes(frame)

        if cubes_detected:
            detected_frame += 1
        
            if detected_frame > 60: #Object(s) has been detected for more than 60 frames in a row
                valid_cube = False
                while not valid_cube:
                    print("Detected following cube(s):")
                    for i, color in enumerate(cubes_detected):
                        center = centers[i]

                        print(f"     Cube with color {color} at {center}")
                        
                    print("")
                    picked_cube = input("What cube do you want to pick? (cube color/none)")
                    
                    if picked_cube == "none":
                        print("Picking up no cube!\n")
                        valid_cube = True
                    elif picked_cube in cubes_detected:
                        x, y = centers[cubes_detected.index(picked_cube)]
                        x, y = picker.pixel_to_robot_xy(x,y)
                        print(f"Picking up {picked_cube} at position ({x},{y})\n")
                        
                        picker.grasp(x,y)
                        t.sleep(3)

                        valid_cube = True
                    else:
                        print("Cube not detected!\n")    

                detected_frame = 1
        else:
            detected_frame = 1      

        cv2.imshow("frame", frame)
        key = cv2.waitKey(1)

cap.release()
cv2.destroyAllWindows()
sys.exit()
