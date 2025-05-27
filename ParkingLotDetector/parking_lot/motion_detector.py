import json
from pathlib import Path
import cv2 as open_cv
import numpy as np
from drawing_utils import draw_contours
from colors import *
from statuses import *
from ultralytics import YOLO
import torch

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
        # Dynamically set device based on CUDA availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.yolo = YOLO("yolov8n.pt").to(device)

    def detect_motion(self):
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
                lineType=open_cv.LINE_8)

            mask = mask == 255
            self.mask.append(mask)

        statuses = [NOT_DETERMINED] * len(coordinates_data)
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

            for index, p in enumerate(coordinates_data):
                coordinates = self._coordinates(p)
                status = statuses[index]
                color = COLOR_YELLOW
                if status == FREE:
                    color = COLOR_GREEN
                elif status == OCCUPIED:
                    color = COLOR_RED

                draw_contours(new_frame, coordinates, str(p["id"] + 1), COLOR_WHITE, color)

            open_cv.imshow(str(self.video), new_frame)

            status_data = {
                "available_spaces": sum(1 for s in statuses if s == FREE),
                "occupied_spaces": sum(1 for s in statuses if s == OCCUPIED),
                "unknown_spaces": sum(1 for s in statuses if s == NOT_DETERMINED),
                "total": len(statuses)
            }
            output_file = Path("parking_lot_state.json")
            with output_file.open("w") as f:
                json.dump(status_data, f)


            k = open_cv.waitKey(1)
            if k == ord("q"):
                break

        capture.release()
        open_cv.destroyAllWindows()

    def __apply(self, grayed, index, p):
        coordinates = self._coordinates(p)
        rect = self.bounds[index]

        roi_gray = grayed[rect[1]:(rect[1] + rect[3]), rect[0]:(rect[0] + rect[2])]
        laplacian = open_cv.Laplacian(roi_gray, open_cv.CV_64F)

        coordinates[:, 0] = coordinates[:, 0] - rect[0]
        coordinates[:, 1] = coordinates[:, 1] - rect[1]

        laplacian_status = np.mean(np.abs(laplacian * self.mask[index])) < MotionDetector.LAPLACIAN

        roi_color = self.current_frame[rect[1]:(rect[1] + rect[3]), rect[0]:(rect[0] + rect[2])]
        results = self.yolo(roi_color, verbose=False)[0]

        vehicle_classes = [2, 3, 5, 7]
        vehicle_found = any(int(cls.item()) in vehicle_classes for cls in results.boxes.cls)

        if not laplacian_status and vehicle_found:
            return OCCUPIED
        elif not laplacian_status or vehicle_found:
            return NOT_DETERMINED
        else:
            return FREE

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