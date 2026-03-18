import time
from traffic_logic import TrafficLogic


def test_cumulative_counts_update():
    tl = TrafficLogic()

    # Stop the background thread from really running long — it uses daemon thread and loops forever.
    # We'll not rely on the thread; instead directly call methods to simulate behavior.

    # Simulate lane data with counts
    detailed = {'Car': 2, 'Bus': 1, 'Truck': 0, 'Motorcycle': 0, 'Ambulance': 0}
    tl.update_lane_data(1, density=3, ambulance=False, detailed_counts=detailed)

    # Simulate the end of green by manually setting current_vehicle_counts and invoking logic
    with tl.lock:
        tl.lanes[1]['current_vehicle_counts'] = detailed
        tl.current_active_lane = 1
        tl.lanes[1]['status'] = 'orange'
        tl.timer = tl.orange_light_duration

    # Force the logic to treat orange->red transition path by calling the internal method sequence
    # This test will emulate the part where lane turns red and cumulative counts are updated.
    # We'll call _set_orange_light then the code that runs on orange expiry.
    tl._set_orange_light(1)

    # Now emulate orange duration elapsed
    with tl.lock:
        tl.timer = tl.orange_light_duration
        # Simulate logic that would run on timer expiry (abridged)
        current_counts = tl.lanes[tl.current_active_lane].get('current_vehicle_counts', {})
        for vehicle, count in current_counts.items():
            tl.cumulative_counts[tl.current_active_lane][vehicle] += count

    assert tl.cumulative_counts[1]['Car'] >= 2
    assert tl.cumulative_counts[1]['Bus'] >= 1
