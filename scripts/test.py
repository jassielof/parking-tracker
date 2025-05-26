import requests
import time
import os

API_BASE = "http://127.0.0.1:8000/api/parking"

def test_create_parking_lot():
    """Create a new parking lot using the API"""
    files = {
        'name': (None, 'Test Parking Lot'),
        'image_file': ('parking_lot_1.png', open('/home/jassielof/GitHub/jassielof/parking-tracker/assets/images/parking_lot_1.png', 'rb'), 'image/png'),
        'video_file': ('parking_lot_1.mp4', open('/home/jassielof/GitHub/jassielof/parking-tracker/assets/videos/parking_lot_1.mp4', 'rb'), 'video/mp4'),
        'start_frame': (None, '1'),
    }

    response = requests.post(f"{API_BASE}/lots/", files=files)
    print(f"Create response: {response.status_code}")
    print(response.json())

    # Return the ID of the created parking lot
    return response.json().get('id')

def test_get_status(lot_id=None):
    """Get parking status"""
    # Get all statuses
    response = requests.get(f"{API_BASE}/status/")
    print(f"Status response: {response.status_code}")
    print(response.json())

    # Get specific lot if ID provided
    if lot_id:
        response = requests.get(f"{API_BASE}/lots/{lot_id}/")
        print(f"Lot detail response: {response.status_code}")
        print(response.json())

def main():
    # Create a new parking lot
    lot_id = test_create_parking_lot()

    # Wait for detection to initialize
    print("Waiting for detector to initialize (15 seconds)...")
    time.sleep(15)

    # Get status updates
    print("Getting status updates...")
    for i in range(3):
        test_get_status(lot_id)
        time.sleep(5)

if __name__ == "__main__":
    main()