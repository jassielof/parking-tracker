# filepath: /home/jassielof/GitHub/jassielof/parking-tracker/parking_detection/models.py
from django.db import models
import uuid

class ParkingLot(models.Model):
    """Model representing a parking lot"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, default="Unnamed Parking Lot")
    image_path = models.CharField(max_length=255, null=True, blank=True)
    video_path = models.CharField(max_length=255, null=True, blank=True)
    data_path = models.CharField(max_length=255, null=True, blank=True)
    start_frame = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = "Parking Lot"
        verbose_name_plural = "Parking Lots"


class ParkingStatus(models.Model):
    """Model representing the current status of a parking lot"""
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='statuses')
    total_spaces = models.IntegerField(default=0)
    free_spaces = models.IntegerField(default=0)
    occupied_spaces = models.IntegerField(default=0)
    unknown_spaces = models.IntegerField(default=0)
    raw_statuses = models.JSONField(default=list, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parking_lot.name} - {self.free_spaces}/{self.total_spaces} free"

    class Meta:
        verbose_name = "Parking Status"
        verbose_name_plural = "Parking Statuses"
        ordering = ['-timestamp']
        get_latest_by = "timestamp"