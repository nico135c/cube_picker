import cv2
import numpy as np
import os
import time as t
from pymycobot import MyCobot280
import RPi.GPIO as GPIO


class CubePicker:
    def __init__(self, serial_port=None, baud=1_000_000, camera_index=0):
        # --- Hardware handles ---
        self.mc = None
        self.cap = None
        self.camera_index = camera_index

        # --- Vision/Calibration state ---
        self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
        self.aruco_params = cv2.aruco.DetectorParameters_create()
        self.aruco_centers = []  # rolling collection for averaging
        self.c1X = self.c1Y = self.c2X = self.c2Y = 0
        self.aruco1_center = None
        self.aruco2_center = None
        self.real_aruco1_center = (58,100)
        self.real_aruco2_center = (-58,215)
        self.M = None  # affine (image->robot XY)

        # --- Color ranges & drawing colors ---
        self.HSV = {
            "blue":   [np.array([96, 122, 139]), np.array([132, 255, 255])],
            "green":  [np.array([77, 69, 64]),  np.array([91, 255, 255])],
            "yellow": [np.array([22, 100, 100]), np.array([30, 255, 255])],
            "red":    [np.array([0, 107, 149]),  np.array([8, 255, 255])],
        }
        self.colors = {
            "blue":   [160, 133, 56],
            "green":  [106, 144, 41],
            "yellow": [91, 196, 204],
            "red":    [82, 100, 197],
        }

        # --- Motion presets ---
        self.move_angles = [
            [0.61, 45.87, -92.37, -41.3, 2.02, 9.58],      # idle/home
            [18.8, -7.91, -54.49, -23.02, -0.79, -14.76],  # pre-grasp
        ]

        self.move_coords = {
            "blue": [132.2, -136.9, 200.8, -178.24, -3.72, -107.17],  # D Sorting area
            "green": [238.8, -136.9, 204.3, -169.69, -5.52, -96.52], # C Sorting area
            "yellow": [115.8, 177.3, 210.6, 178.06, -0.92, -6.11], # A Sorting area
            "red": [-6.9, 173.2, 201.5, 179.93, 0.63, 33.83], # B Sorting area
        }

        # --- GPIO / gripper ---
        self.GPIO = GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(20, GPIO.OUT)
        GPIO.setup(21, GPIO.OUT)
        GPIO.output(20, 1)
        GPIO.output(21, 1)

        # --- Robot init ---
        port = serial_port or os.popen("ls /dev/ttyAMA*").readline().strip()
        self.mc = MyCobot280(port, baud)
        self.mc.power_on()
        self.mc.send_angles(self.move_angles[0], 20)
        t.sleep(2.5)

    # ========== Camera lifecycle ==========
    def open_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.cap.open(self.camera_index)

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

    # ========== Init and Calibration ==========
    def initialize(self, init_frames=12):
        """Find rough crop corners by averaging ArUco centers over a few full frames."""
        self.open_camera()
        self.aruco_centers.clear()
        for _ in range(init_frames):
            ok, frame = self.cap.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if not ok: continue
            self._detect_aruco_into_buffer(frame)
        self._set_crop_corners()

    def calibrate(self, calib_frames=60):
        """Refine ArUco centers on cropped frames and compute image->robot mapping."""
        self.aruco_centers.clear()
        for _ in range(calib_frames):
            ok, frame = self.cap.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if not ok: continue
            frame = self.crop_frame(frame)
            self._detect_aruco_into_buffer(frame)
        self._finalize_aruco_and_affine()

    # ========== Vision ==========
    def crop_frame(self, frame):
        x_min, x_max = sorted([self.c1X, self.c2X])
        y_min, y_max = sorted([self.c1Y, self.c2Y])
        cropped = frame[y_min:y_max, x_min:x_max]
        cropped = cv2.resize(cropped, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        return cropped

    def detect_objects(self, img):
        objects, centers = [], []
        # --- DETECTING CUBES ---
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        for color, (lower, upper) in self.HSV.items():
            rgb = self.colors[color]
            mask = cv2.inRange(hsv, lower, upper)
            _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                if cv2.contourArea(c) > 10000:
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(img, (x, y), (x + w, y + h), rgb, 2)
                    cx, cy = (x + w // 2, y + h // 2)
                    cv2.circle(img, (cx, cy), 3, (255, 255, 255), -1)
                    objects.append(f"{color} cube")
                    centers.append([cx, cy])
        return objects, centers

    def pixel_to_robot_xy(self, x, y):
        if self.M is None:
            raise RuntimeError("Affine transform M not set. Call calibrate() first.")
        pt = np.array([x, y, 1.0], dtype=np.float32)
        X, Y = (self.M @ pt)
        return float(X), float(Y)

    # ========== Motion / Gripper ==========
    def set_gripper(self, on: bool):
        # active-low example; adjust if your wiring is different
        if on:
            self.GPIO.output(20, 0)
            self.GPIO.output(21, 0)
        else:
            self.GPIO.output(20, 1)
            self.GPIO.output(21, 1)

    def grasp(self, x, y, obj):
        print(f"[GRASP] Grasping {obj} at position ({x},{y})")
        x, y = y, x
        # Pre-position
        self.mc.send_angles(self.move_angles[1], 25); t.sleep(3)
        
        # Approach
        self.mc.send_coords([x, y, 170.6, 179.87, -3.78, -62.75], 25, 1); t.sleep(3)
        
        # Descend & grip
        # Check if object is a cube, adjust gripping depth accordingly
        if "cube" in obj.lower():
            self.mc.send_coords([x, y, 103.0, 179.87, -3.78, -62.75], 25, 0); t.sleep(2)
        else:
            self.mc.send_coords([x, y, 65, 179.87, -3.78, -62.75], 25, 0); t.sleep(2)
        
        
        self.set_gripper(True); t.sleep(0.5)
        
        # Lift
        self.mc.send_coords([x, y, 170.6, 179.87, -3.78, -62.75], 25, 1); t.sleep(2)
        
        # Go to sorting bin
        if "cube" in obj.lower():
            self.mc.send_coords(self.move_coords[obj.replace(" cube", "")], 25); t.sleep(0.5)
            self.set_gripper(False); t.sleep(4.5)
        else: 
            self.mc.send_coords(self.move_coords["yellow"], 25)
            self.set_gripper(False); t.sleep(7)

        # Return
        self.mc.send_angles(self.move_angles[1], 25); t.sleep(2)
        self.mc.send_angles(self.move_angles[0], 25)

    # ---------- helpers (internal) ----------
    def _detect_aruco_into_buffer(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        corners, _, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)
        centers = []
        for corner in corners:
            pts = corner[0]
            centers.append([int(pts[:, 0].mean()), int(pts[:, 1].mean())])
        self.aruco_centers.append(centers)

    def _set_crop_corners(self):
        x1s, y1s, x2s, y2s = [], [], [], []
        for centers in self.aruco_centers:
            if len(centers) >= 2:
                (x1, y1), (x2, y2) = centers[0], centers[1]
                x1s.append(x1); y1s.append(y1); x2s.append(x2); y2s.append(y2)
        if not x1s or not x2s:
            raise RuntimeError("ArUco not found during initialize().")
        self.c1X = int(np.mean(x1s)) - 28
        self.c1Y = int(np.mean(y1s)) + 28
        self.c2X = int(np.mean(x2s)) + 28
        self.c2Y = int(np.mean(y2s)) - 28
        self.aruco_centers.clear()

    def _finalize_aruco_and_affine(self):
        x1s, y1s, x2s, y2s = [], [], [], []
        for centers in self.aruco_centers:
            if len(centers) >= 2:
                (x1, y1), (x2, y2) = centers[0], centers[1]
                x1s.append(x1); y1s.append(y1); x2s.append(x2); y2s.append(y2)
        if not x1s or not x2s:
            raise RuntimeError("ArUco not found during calibrate().")
        self.aruco1_center = (int(np.mean(x1s)), int(np.mean(y1s)))
        self.aruco2_center = (int(np.mean(x2s)), int(np.mean(y2s)))
        self.aruco_centers.clear()

        image_pts = np.asarray([self.aruco1_center, self.aruco2_center], dtype=np.float32)
        robot_xy  = np.asarray([self.real_aruco1_center, self.real_aruco2_center], dtype=np.float32)
        M, _ = cv2.estimateAffinePartial2D(image_pts, robot_xy, method=cv2.LMEDS)
        if M is None:
            raise RuntimeError("Failed to compute affine transform.")
        self.M = M
