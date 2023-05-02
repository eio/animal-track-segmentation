import numpy as np
from haversine import haversine, Unit

# Constants
EARTH_RADIUS = 6371 * 1000  # meters
# Define strings for column/feature names
LATITUDE = "lat"
LONGITUDE = "lon"
TIMESTAMP = "timestamp"
VELOCITY = "velocity"
BEARING = "bearing"
TURN_ANGLE = "turn_angle"


def calculate_velocity_bearing_turn(df, burst_time_threshold):
    # Ensure the index of the DataFrame is sequential after grouping
    df = df.reset_index(drop=True)
    # Convert latitude and longitude to radians
    lat_rad = np.radians(df[LATITUDE])
    lon_rad = np.radians(df[LONGITUDE])
    # Calculate spatial distances between consecutive rows
    dist = calculate_spatial_differences(lat_rad, lon_rad)  # meters
    # Calculate temporal differences between consecutive rows
    time_diff = calculate_time_differences(df)  # seconds
    # Identify the bursts
    burst_indices = identify_bursts(df, burst_time_threshold)
    # Calculate velocity, bearing, and turn angle for each burst
    for i in range(len(burst_indices) - 1):
        start_idx = burst_indices[i]
        end_idx = burst_indices[i + 1]
        if end_idx >= len(df):
            # Exit the loop if the end index is too high
            break
        # Calculate velocity, bearing, and turn angle:
        velocity = calculate_velocity(
            dist[start_idx:end_idx], time_diff[start_idx:end_idx]
        )
        bearing = calculate_bearing(
            lat_rad[start_idx : end_idx + 1], lon_rad[start_idx : end_idx + 1]
        )
        turn_angle = calculate_turn_angle(bearing)
        # Add velocity, bearing, and turn angle columns to the dataframe
        df.loc[start_idx + 1 : end_idx, VELOCITY] = velocity
        df.loc[start_idx + 1 : end_idx, BEARING] = bearing
        df.loc[start_idx + 1 : end_idx, TURN_ANGLE] = turn_angle
    # Fill NaN values with 0
    df.fillna(0, inplace=True)
    return df


def identify_bursts(df, burst_time_threshold):
    dt = np.diff(df[TIMESTAMP])
    burst_indices = [0]
    for i in range(1, len(dt)):
        if dt[i - 1] > burst_time_threshold:
            burst_indices.append(i)
    # print("burst_indices:", len(burst_indices))
    return burst_indices


def calculate_velocity(dist, dt):
    velocity = dist[0] / dt.iloc[0]
    return velocity


def calculate_bearing(lat_rad, lon_rad):
    x = np.cos(lat_rad) * np.sin(np.diff(lon_rad))
    y = (np.sin(lat_rad) * np.cos(lat_rad)) - (
        np.cos(lat_rad) * np.sin(lat_rad) * np.cos(lon_rad - lon_rad.iloc[0])
    )
    # Handle wrap-around at the international dateline
    bearing = np.degrees(np.arctan2(x, y)) % 360
    return bearing


def calculate_turn_angle(bearing):
    turn_angle = np.degrees(
        np.arccos(np.clip(np.cos(np.radians(bearing - np.roll(bearing, 1))), -1, 1))
    )
    # Fill NaN values with 0
    turn_angle[np.isnan(turn_angle)] = 0
    return turn_angle


def calculate_spatial_differences(lat_rad, lon_rad):
    # Calculate spatial distances between consecutive rows
    dist = []
    for i in range(1, len(lat_rad)):
        lat1, lon1 = lat_rad[i - 1], lon_rad[i - 1]
        lat2, lon2 = lat_rad[i], lon_rad[i]
        # Apply the Haversine formula to calculate the spatial difference
        dist.append(haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS))
    # First element has distance of 0 meters
    return [0.0] + dist


def calculate_time_differences(df):
    # Calculate time differences between consecutive rows
    time_diff = df[TIMESTAMP].diff().dt.total_seconds().astype("float64")
    # Replace null first element with time difference of 0
    time_diff[0] = 0
    return time_diff
