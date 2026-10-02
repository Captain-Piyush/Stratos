import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database.connection import db

logger = logging.getLogger(__name__)

def parse_date(date_str):
    if not date_str or pd.isna(date_str):
        return pd.NaT
    try:
        return pd.to_datetime(date_str.replace("Z", "+00:00"))
    except:
        return pd.NaT

def build_feature_dataset(
    session_key: int,
    max_lap: Optional[int] = None,
    cutoff_time: Optional[datetime] = None
) -> pd.DataFrame:
    """Build the feature dataset for a given session, optionally bounding by lap and time."""
    
    if db.db is None:
        db.connect()
        
    logger.info(f"Building feature dataset for session {session_key}")
    
    # 1. Load Base Laps
    lap_query = {"session_key": session_key}
    if max_lap is not None:
        lap_query["lap_number"] = {"$lte": max_lap}
    laps_cursor = db.get_collection("laps").find(lap_query)
    laps_df = pd.DataFrame(list(laps_cursor))
    
    if laps_df.empty:
        logger.warning(f"No laps found for session {session_key}")
        return pd.DataFrame()
        
    # Standardize dates and numeric fields
    laps_df['lap_duration'] = pd.to_numeric(laps_df['lap_duration'], errors='coerce')
    laps_df['date_start'] = laps_df['date_start'].apply(parse_date)
    laps_df['lap_end_time'] = laps_df.apply(
        lambda row: row['date_start'] + pd.Timedelta(seconds=row['lap_duration']) 
        if not pd.isna(row['date_start']) and pd.notnull(row['lap_duration']) else pd.NaT, 
        axis=1
    )
    
    # 2. Load Stints & Pit Stops (bound by lap)
    stints_df = pd.DataFrame(list(db.get_collection("stints").find(lap_query)))
    pits_df = pd.DataFrame(list(db.get_collection("pit_stops").find(lap_query)))
    
    # 3. Load Race Control (bound by time if available)
    rc_query = {"session_key": session_key}
    if cutoff_time is not None:
        rc_query["date"] = {"$lte": cutoff_time.strftime("%Y-%m-%dT%H:%M:%S%z") if cutoff_time.tzinfo else cutoff_time.isoformat()}
    rc_df = pd.DataFrame(list(db.get_collection("race_control").find(rc_query)))
    if not rc_df.empty:
        rc_df['date'] = rc_df['date'].apply(parse_date)
        rc_df = rc_df.sort_values('date')
    
    # 4. Process each driver-lap securely to prevent data leakage
    features = []
    
    drivers = laps_df['driver_number'].unique()
    
    for driver in drivers:
        d_laps = laps_df[laps_df['driver_number'] == driver].sort_values('lap_number').copy()
        
        # Merge Stints
        if not stints_df.empty:
            d_stints = stints_df[stints_df['driver_number'] == driver]
            
            def get_stint_info(lap):
                # Find stint where lap_start <= lap <= lap_end
                # Also handle missing lap_end (assume 999)
                for _, s in d_stints.iterrows():
                    l_start = s.get('lap_start', 0)
                    l_end = s.get('lap_end') if pd.notnull(s.get('lap_end')) else 999
                    if l_start <= lap <= l_end:
                        return s['compound'], s['tyre_age_at_start'], s['stint_number'], l_start
                return None, 0, None, None
                
            d_laps[['tyre_compound', 'tyre_age_at_start', 'stint_number', 'stint_lap_start']] = d_laps['lap_number'].apply(
                lambda x: pd.Series(get_stint_info(x))
            )
            d_laps['tyre_age'] = d_laps['lap_number'] - d_laps['stint_lap_start'] + d_laps['tyre_age_at_start'] + 1
            d_laps['stint_lap_number'] = d_laps['lap_number'] - d_laps['stint_lap_start'] + 1
        else:
            d_laps['tyre_compound'] = None
            d_laps['tyre_age'] = None
            d_laps['stint_number'] = None
            d_laps['stint_lap_number'] = None
            
        # Merge Pits
        d_laps['pit_in'] = False
        d_laps['pit_out'] = False
        d_laps['laps_since_pit'] = d_laps['stint_lap_number'] # Approximation
        
        if not pits_df.empty:
            d_pits = pits_df[pits_df['driver_number'] == driver]
            pit_laps = d_pits['lap_number'].tolist()
            d_laps['pit_in'] = d_laps['lap_number'].isin(pit_laps)
        
        d_laps['pit_out'] = d_laps['is_pit_out_lap'].fillna(False).astype(bool)
        
        # Validation Flags & Context
        # A lap is valid if it has a duration, is not an out lap, not a pit in lap, 
        # and not affected by SC/VSC/Red Flag
        
        def check_race_control(lap_start, lap_end):
            if pd.isna(lap_start) or pd.isna(lap_end) or rc_df.empty:
                return False, False, False
            
            # Look for active flags intersecting this lap time
            # For simplicity, if any SC/VSC/Red flag occurred between start and end, or was active at start
            # This is an approximation since RC messages don't always give clear "CLEAR" messages
            # For Phase 2, we just check if a message occurred during the lap
            msgs = rc_df[(rc_df['date'] >= lap_start) & (rc_df['date'] <= lap_end)]
            sc = msgs['message'].str.contains('SAFETY CAR', case=False, na=False).any()
            vsc = msgs['message'].str.contains('VIRTUAL SAFETY CAR', case=False, na=False).any()
            red = msgs['message'].str.contains('RED FLAG', case=False, na=False).any()
            return sc, vsc, red
            
        rc_flags = d_laps.apply(lambda row: check_race_control(row['date_start'], row['lap_end_time']), axis=1)
        if not rc_flags.empty:
            d_laps['safety_car_active'], d_laps['virtual_safety_car_active'], d_laps['red_flag_context'] = zip(*rc_flags)
        else:
            d_laps['safety_car_active'] = False
            d_laps['virtual_safety_car_active'] = False
            d_laps['red_flag_context'] = False
            
        d_laps['lap_time_valid'] = (
            pd.notnull(d_laps['lap_duration']) & 
            ~d_laps['pit_in'] & 
            ~d_laps['pit_out'] & 
            ~d_laps['safety_car_active'] & 
            ~d_laps['virtual_safety_car_active'] & 
            ~d_laps['red_flag_context']
        )
        
        # Pace Features (Rolling windows over VALID laps only)
        # Using shift() prevents data leakage (we only use past laps to calculate pace for this lap context)
        # However, typically "lap N pace features" means "pace AT lap N", which *includes* lap N.
        # But if this is a feature to PREDICT lap N, we must shift.
        # The prompt says "No feature may use future race information when representing the state at lap N."
        # Using lap N lap_time to represent state AT lap N is fine.
        
        valid_laps = d_laps[d_laps['lap_time_valid']]['lap_duration']
        
        d_laps['rolling_mean_pace_3'] = valid_laps.rolling(window=3, min_periods=1).mean()
        d_laps['rolling_mean_pace_5'] = valid_laps.rolling(window=5, min_periods=1).mean()
        d_laps['rolling_mean_pace_10'] = valid_laps.rolling(window=10, min_periods=1).mean()
        
        def calculate_trend(series):
            if len(series.dropna()) < 3:
                return np.nan
            x = np.arange(len(series.dropna()))
            y = series.dropna().values
            return np.polyfit(x, y, 1)[0]
            
        d_laps['pace_trend'] = valid_laps.rolling(window=5, min_periods=3).apply(calculate_trend, raw=False)
        
        # Stint baseline and degradation
        d_laps['lap_time_vs_stint_baseline'] = np.nan
        d_laps['pace_change_with_tyre_age'] = np.nan
        
        for stint in d_laps['stint_number'].dropna().unique():
            stint_idx = (d_laps['stint_number'] == stint) & d_laps['lap_time_valid']
            stint_data = d_laps[stint_idx]
            if len(stint_data) > 0:
                baseline = stint_data.iloc[0]['lap_duration']
                d_laps.loc[stint_idx, 'lap_time_vs_stint_baseline'] = stint_data['lap_duration'] - baseline
                
                # Expanding trend for degradation
                d_laps.loc[stint_idx, 'pace_change_with_tyre_age'] = stint_data['lap_duration'].expanding(min_periods=3).apply(calculate_trend, raw=False)
                
        features.append(d_laps)
        
    if not features:
        return pd.DataFrame()
        
    master_df = pd.concat(features, ignore_index=True)
    
    # 5. Bring in Positions and Intervals (Time-Aligned to prevent leakage)
    # Bound queries by cutoff_time if provided
    time_query = {"session_key": session_key}
    if cutoff_time is not None:
        # DB dates are strings in isoformat, usually with Z. We can just use string comparison if formatted correctly, 
        # but safely we fetch and filter in pandas, OR we use $lte on string (which works for ISO-8601).
        # We will just fetch all for the session and filter in pandas using the parsed dates to be absolutely safe with formats,
        # OR we could query it. Let's rely on pandas filtering to avoid string format mismatches in MongoDB.
        pass
        
    positions_df = pd.DataFrame(list(db.get_collection("positions").find({"session_key": session_key})))
    if not positions_df.empty:
        positions_df['date'] = positions_df['date'].apply(parse_date)
        if cutoff_time is not None:
            positions_df = positions_df[positions_df['date'] <= cutoff_time]
        positions_df = positions_df.sort_values('date')
    
    intervals_df = pd.DataFrame(list(db.get_collection("intervals").find({"session_key": session_key})))
    if not intervals_df.empty:
        intervals_df['date'] = intervals_df['date'].apply(parse_date)
        if cutoff_time is not None:
            intervals_df = intervals_df[intervals_df['date'] <= cutoff_time]
        intervals_df = intervals_df.sort_values('date')
        
    weather_df = pd.DataFrame(list(db.get_collection("weather").find({"session_key": session_key})))
    if not weather_df.empty:
        weather_df['date'] = weather_df['date'].apply(parse_date)
        if cutoff_time is not None:
            weather_df = weather_df[weather_df['date'] <= cutoff_time]
        weather_df = weather_df.sort_values('date')
        
    logger.info("Aligning timestamps for positions, intervals, and weather")
    
    master_df['position'] = np.nan
    master_df['gap_to_leader'] = np.nan
    master_df['gap_to_ahead'] = np.nan
    master_df['gap_valid'] = False
    master_df['air_temperature'] = np.nan
    master_df['track_temperature'] = np.nan
    master_df['humidity'] = np.nan
    master_df['rainfall'] = np.nan
    master_df['weather_alignment_quality'] = "POOR"
    
    def fetch_time_aligned_data(row):
        end_time = row['lap_end_time']
        dn = row['driver_number']
        if pd.isna(end_time):
            return pd.Series({'position': np.nan, 'gap_to_leader': np.nan, 'gap_to_ahead': np.nan, 'gap_valid': False,
                              'air_temperature': np.nan, 'track_temperature': np.nan, 'humidity': np.nan,
                              'rainfall': np.nan, 'weather_alignment_quality': "POOR"})
                              
        # Position
        pos = np.nan
        if not positions_df.empty:
            driver_pos = positions_df[(positions_df['driver_number'] == dn) & (positions_df['date'] <= end_time)]
            if not driver_pos.empty:
                pos = driver_pos.iloc[-1]['position']
                
        # Interval
        gap = np.nan
        gap_ahead = np.nan
        gap_valid = False
        if not intervals_df.empty:
            driver_int = intervals_df[(intervals_df['driver_number'] == dn) & (intervals_df['date'] <= end_time)]
            if not driver_int.empty:
                last_int = driver_int.iloc[-1]
                gap = last_int.get('gap_to_leader', np.nan)
                gap_ahead = last_int.get('interval', np.nan)
                # Check if the gap data is reasonably fresh (within 3 minutes)
                time_diff = (end_time - last_int['date']).total_seconds()
                if time_diff < 180:
                    gap_valid = True
                    
        # Weather
        air, track, hum, rain, quality = np.nan, np.nan, np.nan, np.nan, "POOR"
        if not weather_df.empty:
            w = weather_df[weather_df['date'] <= end_time]
            if not w.empty:
                last_w = w.iloc[-1]
                air = last_w.get('air_temperature', np.nan)
                track = last_w.get('track_temperature', np.nan)
                hum = last_w.get('humidity', np.nan)
                rain = last_w.get('rainfall', np.nan)
                
                # Check quality
                w_time_diff = (end_time - last_w['date']).total_seconds()
                if w_time_diff <= 300:
                    quality = "GOOD"
                elif w_time_diff <= 900:
                    quality = "FAIR"
                    
        return pd.Series({'position': pos, 'gap_to_leader': gap, 'gap_to_ahead': gap_ahead, 'gap_valid': gap_valid,
                          'air_temperature': air, 'track_temperature': track, 'humidity': hum,
                          'rainfall': rain, 'weather_alignment_quality': quality})

    # Apply the fetch logic
    aligned_data = master_df.apply(fetch_time_aligned_data, axis=1)
    for col in aligned_data.columns:
        master_df[col] = aligned_data[col]
    
    # Sort for shift operations
    master_df = master_df.sort_values(['driver_number', 'lap_number'])
    master_df['position_change'] = master_df.groupby('driver_number')['position'].diff().fillna(0).astype(int)
    master_df['gap_to_ahead'] = pd.to_numeric(master_df['gap_to_ahead'], errors='coerce')
    master_df['gap_to_leader'] = pd.to_numeric(master_df['gap_to_leader'], errors='coerce')
    master_df['gap_change'] = master_df.groupby('driver_number')['gap_to_ahead'].diff()
    master_df['closing_rate'] = -master_df['gap_change'] # Positive means closing the gap
    
    # Calculate Traffic and Inter-Driver gaps by lap
    master_df['cars_within_1s'] = 0
    master_df['cars_within_2s'] = 0
    master_df['gap_to_behind'] = np.nan
    master_df['opening_rate'] = np.nan
    master_df['following_driver'] = np.nan
    master_df['driver_being_followed'] = np.nan
    master_df['relative_pace_to_nearby_drivers'] = np.nan
    
    # Also attach team name
    drivers_df = pd.DataFrame(list(db.get_collection("drivers").find({"session_key": session_key})))
    if not drivers_df.empty:
        driver_team_map = dict(zip(drivers_df['driver_number'], drivers_df['team_name']))
        master_df['team_name'] = master_df['driver_number'].map(driver_team_map)
    else:
        master_df['team_name'] = None
        
    master_df['teammate_pace_delta'] = np.nan
    
    for lap in master_df['lap_number'].unique():
        # Process lap by lap
        lap_idx = master_df['lap_number'] == lap
        lap_data = master_df[lap_idx].sort_values('position')
        
        # Team delta
        for team in lap_data['team_name'].dropna().unique():
            team_drivers = lap_data[lap_data['team_name'] == team]
            if len(team_drivers) == 2:
                idx1, idx2 = team_drivers.index[0], team_drivers.index[1]
                t1, t2 = master_df.at[idx1, 'lap_duration'], master_df.at[idx2, 'lap_duration']
                if pd.notnull(t1) and pd.notnull(t2):
                    master_df.at[idx1, 'teammate_pace_delta'] = t1 - t2
                    master_df.at[idx2, 'teammate_pace_delta'] = t2 - t1
        
        # Gaps and Traffic
        valid_pos = lap_data.dropna(subset=['gap_to_leader', 'position'])
        # Coerce gap_to_leader to numeric (deals with '+1 LAP' strings)
        valid_pos['gap_to_leader'] = pd.to_numeric(valid_pos['gap_to_leader'], errors='coerce')
        valid_pos = valid_pos.dropna(subset=['gap_to_leader'])
        
        if not valid_pos.empty:
            gaps = valid_pos['gap_to_leader'].values
            pos_indices = valid_pos.index
            drivers_list = valid_pos['driver_number'].values
            lap_times = valid_pos['lap_duration'].values
            
            for i, idx in enumerate(pos_indices):
                gap = gaps[i]
                diffs = np.abs(gaps - gap)
                cars_1s = np.sum(diffs <= 1.0) - 1
                cars_2s = np.sum(diffs <= 2.0) - 1
                master_df.at[idx, 'cars_within_1s'] = max(0, cars_1s)
                master_df.at[idx, 'cars_within_2s'] = max(0, cars_2s)
                
                # Gap to behind is gap of car behind to leader - my gap to leader
                if i < len(pos_indices) - 1:
                    master_df.at[idx, 'gap_to_behind'] = gaps[i+1] - gap
                    master_df.at[idx, 'following_driver'] = drivers_list[i+1]
                
                # Driver being followed is driver ahead
                if i > 0:
                    master_df.at[idx, 'driver_being_followed'] = drivers_list[i-1]
                    
                # Relative pace to nearby drivers (average of car ahead and behind)
                nearby_paces = []
                if i > 0 and pd.notnull(lap_times[i-1]): nearby_paces.append(lap_times[i-1])
                if i < len(lap_times) - 1 and pd.notnull(lap_times[i+1]): nearby_paces.append(lap_times[i+1])
                if nearby_paces and pd.notnull(lap_times[i]):
                    master_df.at[idx, 'relative_pace_to_nearby_drivers'] = lap_times[i] - np.mean(nearby_paces)
                    
    # Calculate opening rate based on gap_to_behind
    master_df = master_df.sort_values(['driver_number', 'lap_number'])
    master_df['opening_rate'] = master_df.groupby('driver_number')['gap_to_behind'].diff()
    
    # Select final columns conforming to schema
    from analytics.features.schema import FEATURE_SCHEMA
    
    # Add lap_time alias
    master_df['lap_time'] = master_df['lap_duration']
    
    final_columns = [col for col in FEATURE_SCHEMA.keys() if col in master_df.columns]
    
    master_df = master_df[final_columns]
    
    logger.info(f"Feature dataset built with {len(master_df)} rows")
    return master_df

if __name__ == "__main__":
    df = build_feature_dataset(7953)
    if not df.empty:
        print(f"Dataset generated. Shape: {df.shape}")
        print("Sample Data (First 2 valid laps for Driver 1):")
        print(df[(df['driver_number'] == 1) & (df['lap_time_valid'])].head(2).to_dict(orient='records'))
