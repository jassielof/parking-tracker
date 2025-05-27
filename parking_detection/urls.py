from django.urls import path
from .views import ParkingLotListView, ParkingLotDetailView, ParkingStatusView

urlpatterns = [
    path('lots/', ParkingLotListView.as_view(), name='parking_lot_list'),
    path('lots/<uuid:pk>/', ParkingLotDetailView.as_view(), name='parking_lot_detail'),
    path('status/', ParkingStatusView.as_view(), name='parking_status'),
    path('availability/', ParkingLotListView.as_view(), name='availability'),
]