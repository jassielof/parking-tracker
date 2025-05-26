from django.contrib import admin
from .models import ParkingLot, ParkingStatus

@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(ParkingStatus)
class ParkingStatusAdmin(admin.ModelAdmin):
    list_display = ('parking_lot', 'free_spaces', 'total_spaces', 'timestamp')
    list_filter = ('parking_lot',)
    date_hierarchy = 'timestamp'