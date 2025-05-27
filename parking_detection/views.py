import json
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import yaml
import os
import threading
import uuid
from django.conf import settings

from server.settings import BASE_DIR
from .utils.coordinates_generator import CoordinatesGenerator
from .utils.detector_manager import DetectorManager
from .models import ParkingLot, ParkingStatus
from shared.colors import Color
from shared.statuses import ParkingStatus as ParkingStatusEnum
import logging

logger = logging.getLogger(__name__)

# Initialize detector manager
detector_manager = DetectorManager()
threading.Thread(target=detector_manager.initialize, daemon=True).start()

class ParkingLotListView(APIView):
    """API endpoint for listing and creating parking lots"""
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """Get list of all parking lots with their status"""
        parking_lots = ParkingLot.objects.filter(is_active=True)
        data = []

        for lot in parking_lots:
            status_data = {
                'id': str(lot.id),
                'name': lot.name,
                'created_at': lot.created_at,
                'updated_at': lot.updated_at,
            }

            try:
                # Get latest status
                latest_status = lot.statuses.latest()
                status_data.update({
                    'total_spaces': latest_status.total_spaces,
                    'free_spaces': latest_status.free_spaces,
                    'occupied_spaces': latest_status.occupied_spaces,
                    'unknown_spaces': latest_status.unknown_spaces,
                    'status_updated_at': latest_status.timestamp
                })
            except ParkingStatus.DoesNotExist:
                status_data.update({
                    'total_spaces': 0,
                    'free_spaces': 0,
                    'occupied_spaces': 0,
                    'unknown_spaces': 0,
                    'status': 'No status available'
                })

            data.append(status_data)

        return Response(data)

    def post(self, request):
        """Create a new parking lot from image/video/data"""
        try:
            name = request.data.get('name', f"Parking Lot {uuid.uuid4().hex[:8]}")
            image_file = request.FILES.get('image_file')
            video_file = request.FILES.get('video_file')
            data_file = request.FILES.get('data_file')
            start_frame = int(request.data.get('start_frame', 1))

            # Create directories if they don't exist
            media_root = settings.MEDIA_ROOT
            os.makedirs(media_root, exist_ok=True)

            lot_id = uuid.uuid4()
            lot_dir = os.path.join(media_root, str(lot_id))
            os.makedirs(lot_dir, exist_ok=True)

            # Create parking lot record
            lot = ParkingLot(
                id=lot_id,
                name=name,
                start_frame=start_frame
            )

            # Process image file if provided
            if image_file:
                image_path = os.path.join(lot_dir, image_file.name)
                with open(image_path, 'wb+') as dest:
                    for chunk in image_file.chunks():
                        dest.write(chunk)
                lot.image_path = image_path

                # If no data file is provided, generate coordinates
                if not data_file:
                    data_path = os.path.join(lot_dir, f"{lot_id}_coordinates.yaml")
                    with open(data_path, 'w+') as points:
                        generator = CoordinatesGenerator(image_path, points, Color.RED)
                        generator.generate()
                    lot.data_path = data_path

            # Process data file if provided
            if data_file:
                data_path = os.path.join(lot_dir, data_file.name)
                with open(data_path, 'wb+') as dest:
                    for chunk in data_file.chunks():
                        dest.write(chunk)
                lot.data_path = data_path

            # Process video file if provided
            if video_file:
                video_path = os.path.join(lot_dir, video_file.name)
                with open(video_path, 'wb+') as dest:
                    for chunk in video_file.chunks():
                        dest.write(chunk)
                lot.video_path = video_path
            else:
                return Response(
                    {"error": "Video file is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save the parking lot
            lot.save()

            # Start detector for this parking lot
            detector_manager.start_detector(lot.id)

            return Response({
                "id": lot.id,
                "name": lot.name,
                "message": "Parking lot created successfully"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating parking lot: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParkingLotDetailView(APIView):
    """API endpoint for individual parking lot operations"""

    def get(self, request, pk):
        """Get details of a specific parking lot"""
        try:
            lot = ParkingLot.objects.get(id=pk)
            data = {
                'id': str(lot.id),
                'name': lot.name,
                'created_at': lot.created_at,
                'updated_at': lot.updated_at,
            }

            try:
                # Get latest status
                latest_status = lot.statuses.latest()
                data.update({
                    'total_spaces': latest_status.total_spaces,
                    'free_spaces': latest_status.free_spaces,
                    'occupied_spaces': latest_status.occupied_spaces,
                    'unknown_spaces': latest_status.unknown_spaces,
                    'status_updated_at': latest_status.timestamp
                })

                # Include raw statuses if requested
                if request.query_params.get('include_raw', '').lower() == 'true':
                    data['raw_statuses'] = latest_status.raw_statuses

            except ParkingStatus.DoesNotExist:
                data.update({
                    'total_spaces': 0,
                    'free_spaces': 0,
                    'occupied_spaces': 0,
                    'unknown_spaces': 0,
                    'status': 'No status available'
                })

            return Response(data)

        except ParkingLot.DoesNotExist:
            return Response(
                {"error": "Parking lot not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, pk):
        """Delete a parking lot (mark as inactive)"""
        try:
            lot = ParkingLot.objects.get(id=pk)

            # Stop detector first
            detector_manager.stop_detector(lot.id)

            # Mark as inactive instead of deleting
            lot.is_active = False
            lot.save()

            return Response({"message": "Parking lot deactivated"})

        except ParkingLot.DoesNotExist:
            return Response(
                {"error": "Parking lot not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class ParkingStatusView(APIView):
    """API endpoint for getting the latest parking status"""

    def get(self, request):
        """Get latest status for all parking lots"""
        data = []

        try:
            # Get all active parking lots
            lots = ParkingLot.objects.filter(is_active=True)

            for lot in lots:
                lot_data = {
                    'id': str(lot.id),
                    'name': lot.name,
                }

                try:
                    # Get latest status
                    latest_status = lot.statuses.latest()
                    lot_data.update({
                        'total_spaces': latest_status.total_spaces,
                        'free_spaces': latest_status.free_spaces,
                        'occupied_spaces': latest_status.occupied_spaces,
                        'updated_at': latest_status.timestamp,
                    })
                except ParkingStatus.DoesNotExist:
                    lot_data.update({
                        'total_spaces': 0,
                        'free_spaces': 0,
                        'occupied_spaces': 0,
                        'status': 'No status available'
                    })

                data.append(lot_data)

            return Response(data)

        except Exception as e:
            logger.error(f"Error fetching parking status: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ParkingAvailabilityView(APIView):
    def get(self, request):
        try:
            json_path = Path(settings.BASE_DIR) / "ParkingLotDetector" / "parking_lot" / "parking_lot_state.json"
            if json_path.exists():
                with json_path.open("r") as f:
                    data = json.load(f)
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Estado no disponible aún"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
