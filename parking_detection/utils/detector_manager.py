import threading
import time
from ..models import ParkingLot, ParkingStatus
from .motion_detector import MotionDetector
import yaml
import os
from shared.statuses import ParkingStatus as ParkingStatusEnum
import logging

logger = logging.getLogger(__name__)

class DetectorManager:
    """Manages all active parking lot detectors"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DetectorManager, cls).__new__(cls)
                cls._instance.detectors = {}
                cls._instance.status_update_thread = None
                cls._instance.running = False

        return cls._instance

    def initialize(self):
        """Initialize the detector manager"""
        if not self.running:
            self.running = True
            self.status_update_thread = threading.Thread(
                target=self._update_statuses_periodically,
                daemon=True
            )
            self.status_update_thread.start()

            # Start detectors for all active parking lots
            self._start_all_detectors()

    def _start_all_detectors(self):
        """Start detectors for all active parking lots in the database"""
        try:
            active_lots = ParkingLot.objects.filter(is_active=True)
            for lot in active_lots:
                self.start_detector(lot.id)
        except Exception as e:
            logger.error(f"Error starting detectors: {e}")

    def start_detector(self, parking_lot_id):
        """Start a detector for a specific parking lot"""
        try:
            # Don't start if already running
            if parking_lot_id in self.detectors:
                return

            # Get parking lot info
            lot = ParkingLot.objects.get(id=parking_lot_id)

            # Check if files exist
            if not (lot.video_path and os.path.exists(lot.video_path) and
                    lot.data_path and os.path.exists(lot.data_path)):
                logger.error(f"Missing files for parking lot {parking_lot_id}")
                return

            # Load coordinates data
            with open(lot.data_path, 'r') as file:
                coordinates_data = yaml.safe_load(file)

            # Create detector
            detector = MotionDetector(lot.video_path, coordinates_data, lot.start_frame)

            # Store detector
            self.detectors[parking_lot_id] = detector

            # Start detection in headless mode
            detector.detect_motion_headless(
                callback=lambda statuses: self._status_callback(parking_lot_id, statuses)
            )

            logger.info(f"Started detector for parking lot {parking_lot_id}")

        except Exception as e:
            logger.error(f"Error starting detector for parking lot {parking_lot_id}: {e}")

    def stop_detector(self, parking_lot_id):
        """Stop a specific detector"""
        if parking_lot_id in self.detectors:
            try:
                self.detectors[parking_lot_id].stop_detection()
                del self.detectors[parking_lot_id]
                logger.info(f"Stopped detector for parking lot {parking_lot_id}")
            except Exception as e:
                logger.error(f"Error stopping detector for parking lot {parking_lot_id}: {e}")

    def get_status(self, parking_lot_id):
        """Get the current status for a specific parking lot"""
        if parking_lot_id in self.detectors:
            return self.detectors[parking_lot_id].get_parking_status()
        return None

    def _status_callback(self, parking_lot_id, statuses):
        """Called when a detector updates its status"""
        try:
            # Count the different statuses
            total = len(statuses)
            free = statuses.count(ParkingStatusEnum.FREE)
            occupied = statuses.count(ParkingStatusEnum.OCCUPIED)
            unknown = statuses.count(ParkingStatusEnum.NOT_DETERMINED)

            # Update status in database (less frequently to avoid DB load)
            # Don't store every update, just periodically
            pass

        except Exception as e:
            logger.error(f"Error in status callback for {parking_lot_id}: {e}")

    def _update_statuses_periodically(self):
        """Update the database with status information periodically"""
        while self.running:
            try:
                # Update status for each active detector
                for parking_lot_id, detector in list(self.detectors.items()):
                    statuses = detector.get_parking_status()
                    if statuses:
                        total = len(statuses)
                        free = statuses.count(ParkingStatusEnum.FREE)
                        occupied = statuses.count(ParkingStatusEnum.OCCUPIED)
                        unknown = statuses.count(ParkingStatusEnum.NOT_DETERMINED)

                        # Update in database
                        ParkingStatus.objects.create(
                            parking_lot_id=parking_lot_id,
                            total_spaces=total,
                            free_spaces=free,
                            occupied_spaces=occupied,
                            unknown_spaces=unknown,
                            raw_statuses=statuses
                        )

                        logger.debug(f"Updated status for {parking_lot_id}: {free}/{total} free")

            except Exception as e:
                logger.error(f"Error updating statuses: {e}")

            # Sleep for a while before next update
            time.sleep(10)  # Update database every 10 seconds to reduce load

    def shutdown(self):
        """Shutdown the detector manager"""
        self.running = False
        for parking_lot_id in list(self.detectors.keys()):
            self.stop_detector(parking_lot_id)