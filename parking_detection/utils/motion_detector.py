import cv2 as open_cv
import numpy as np
from utils.drawing import draw_contours
from shared.colors import Color
from shared.statuses import ParkingStatus
from ultralytics import YOLO
import torch
import threading
import time


class MotionDetector:
    LAPLACIAN = 1.2
    DETECT_DELAY = 1

    def __init__(self, video, coordinates, start_frame):
        self.video = video
        self.coordinates_data = coordinates
        self.start_frame = start_frame
        self.contours = []
        self.bounds = []
        self.mask = []
        self.current_frame = None
        self.running = True
        self.callback = None
        self.current_statuses = None
        # Dynamically set device based on CUDA availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.yolo = YOLO("yolov8n.pt").to(device)

    def detect_motion_headless(self, callback=None):
        """Run detection in background without UI display, for server usage"""
        self.callback = callback
        self.running = True

        # Initialize contours, bounds, and masks
        self._initialize_detection()

        # Start detection in a separate thread
        threading.Thread(target=self._detection_loop, daemon=True).start()

        return self.current_statuses

    def stop_detection(self):
        """Stop the running detection"""
        self.running = False

    def _initialize_detection(self):
        """Initialize detection parameters"""
        coordinates_data = self.coordinates_data
        for p in coordinates_data:
            coordinates = self._coordinates(p)
            rect = open_cv.boundingRect(coordinates)

            new_coordinates = coordinates.copy()
            new_coordinates[:, 0] = coordinates[:, 0] - rect[0]
            new_coordinates[:, 1] = coordinates[:, 1] - rect[1]

            self.contours.append(coordinates)
            self.bounds.append(rect)

            mask = open_cv.drawContours(
                np.zeros((rect[3], rect[2]), dtype=np.uint8),
                [new_coordinates],
                contourIdx=-1,
                color=255,
                thickness=-1,
                lineType=open_cv.LINE_8,
            )

            mask = mask == 255
            self.mask.append(mask)

        # Initialize statuses array
        self.current_statuses = [ParkingStatus.NOT_DETERMINED] * len(coordinates_data)

    def _detection_loop(self):
        """Main detection loop running in background thread"""
        capture = open_cv.VideoCapture(self.video)
        capture.set(open_cv.CAP_PROP_POS_FRAMES, self.start_frame)

        coordinates_data = self.coordinates_data
        statuses = self.current_statuses
        times = [None] * len(coordinates_data)

        frame_index = 0
        while capture.isOpened() and self.running:
            result, frame = capture.read()
            frame_index += 1

            if frame_index % 3 != 0:
                continue

            if frame is None or not result:
                # If we reach the end of video, loop back to start
                capture.set(open_cv.CAP_PROP_POS_FRAMES, self.start_frame)
                continue

            self.current_frame = frame.copy()
            blurred = open_cv.GaussianBlur(frame.copy(), (5, 5), 3)
            grayed = open_cv.cvtColor(blurred, open_cv.COLOR_BGR2GRAY)
            position_in_seconds = capture.get(open_cv.CAP_PROP_POS_MSEC) / 1000.0

            # Process each parking space
            for index, c in enumerate(coordinates_data):
                status = self.__apply(grayed, index, c)

                if times[index] is not None and self.same_status(statuses, index, status):
                    times[index] = None
                    continue

                if times[index] is not None and self.status_changed(statuses, index, status):
                    if position_in_seconds - times[index] >= MotionDetector.DETECT_DELAY:
                        statuses[index] = status
                        times[index] = None
                    continue

                if times[index] is None and self.status_changed(statuses, index, status):
                    times[index] = position_in_seconds

            # Update current statuses
            self.current_statuses = statuses

            # Call the callback if provided
            if self.callback:
                self.callback(statuses)

            # Sleep briefly to avoid hogging CPU
            time.sleep(0.01)

        capture.release()

    def detect_motion(self):
        """Original method with UI display, kept for compatibility"""
        capture = open_cv.VideoCapture(self.video)
        capture.set(open_cv.CAP_PROP_POS_FRAMES, self.start_frame)

        coordinates_data = self.coordinates_data
        for p in coordinates_data:
            coordinates = self._coordinates(p)
            rect = open_cv.boundingRect(coordinates)

            new_coordinates = coordinates.copy()
            new_coordinates[:, 0] = coordinates[:, 0] - rect[0]
            new_coordinates[:, 1] = coordinates[:, 1] - rect[1]

            self.contours.append(coordinates)
            self.bounds.append(rect)

            mask = open_cv.drawContours(
                np.zeros((rect[3], rect[2]), dtype=np.uint8),
                [new_coordinates],
                contourIdx=-1,
                color=255,
                thickness=-1,
                lineType=open_cv.LINE_8,
            )

            mask = mask == 255
            self.mask.append(mask)

        statuses = [ParkingStatus.NOT_DETERMINED] * len(coordinates_data)
        times = [None] * len(coordinates_data)

        frame_index = 0
        while capture.isOpened():
            result, frame = capture.read()
            frame_index += 1

            if frame_index % 3 != 0:
                continue

            if frame is None:
                break
            if not result:
                raise CaptureReadError("Error reading video capture on frame")

            self.current_frame = frame.copy()
            blurred = open_cv.GaussianBlur(frame.copy(), (5, 5), 3)
            grayed = open_cv.cvtColor(blurred, open_cv.COLOR_BGR2GRAY)
            new_frame = frame.copy()
            position_in_seconds = capture.get(open_cv.CAP_PROP_POS_MSEC) / 1000.0

            for index, c in enumerate(coordinates_data):
                status = self.__apply(grayed, index, c)

                if times[index] is not None and self.same_status(
                    statuses, index, status
                ):
                    times[index] = None
                    continue

                if times[index] is not None and self.status_changed(
                    statuses, index, status
                ):
                    if (
                        position_in_seconds - times[index]
                        >= MotionDetector.DETECT_DELAY
                    ):
                        statuses[index] = status
                        times[index] = None
                    continue

                if times[index] is None and self.status_changed(
                    statuses, index, status
                ):
                    times[index] = position_in_seconds

            for index, p in enumerate(coordinates_data):
                coordinates = self._coordinates(p)
                status = statuses[index]
                color = Color.YELLOW
                if status == ParkingStatus.FREE:
                    color = Color.COLOR_GREEN
                elif status == ParkingStatus.OCCUPIED:
                    color = Color.COLOR_RED

                draw_contours(
                    new_frame, coordinates, str(p["id"] + 1), Color.WHITE, color
                )

            open_cv.imshow(str(self.video), new_frame)
            k = open_cv.waitKey(1)
            if k == ord("q"):
                break

        capture.release()
        open_cv.destroyAllWindows()

    def get_parking_status(self):
        """Get the current status of all parking spaces"""
        if self.current_statuses is None:
            return []
        return self.current_statuses

    def __apply(self, grayed, index, p):
        coordinates = self._coordinates(p)
        rect = self.bounds[index]

        roi_gray = grayed[rect[1] : (rect[1] + rect[3]), rect[0] : (rect[0] + rect[2])]
        laplacian = open_cv.Laplacian(roi_gray, open_cv.CV_64F)

        coordinates[:, 0] = coordinates[:, 0] - rect[0]
        coordinates[:, 1] = coordinates[:, 1] - rect[1]

        laplacian_status = (
            np.mean(np.abs(laplacian * self.mask[index])) < MotionDetector.LAPLACIAN
        )

        roi_color = self.current_frame[
            rect[1] : (rect[1] + rect[3]), rect[0] : (rect[0] + rect[2])
        ]
        results = self.yolo(roi_color, verbose=False)[0]

        vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        vehicle_found = any(
            int(cls.item()) in vehicle_classes for cls in results.boxes.cls
        )

        if not laplacian_status and vehicle_found:
            return ParkingStatus.OCCUPIED
        elif not laplacian_status or vehicle_found:
            return ParkingStatus.NOT_DETERMINED
        else:
            return ParkingStatus.FREE

    @staticmethod
    def _coordinates(p):
        return np.array(p["coordinates"])

    @staticmethod
    def same_status(coordinates_status, index, status):
        return status == coordinates_status[index]

    @staticmethod
    def status_changed(coordinates_status, index, status):
        return status != coordinates_status[index]


class CaptureReadError(Exception):
    pass