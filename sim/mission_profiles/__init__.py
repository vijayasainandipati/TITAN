from .endurance import EnduranceMissionProfile
from .hot_weather import HotWeatherMissionProfile
from .high_altitude import HighAltitudeMissionProfile
from .rapid_response import RapidResponseMissionProfile

def get_mission_profile(name: str, duration_hours: float = 8.0, ground_temp_c: float = 25.0):
    name_lower = name.lower()
    if "hot" in name_lower or "desert" in name_lower:
        return HotWeatherMissionProfile(duration_hours=duration_hours, ground_temp_c=max(ground_temp_c, 42.0))
    elif "altitude" in name_lower or "ceiling" in name_lower:
        return HighAltitudeMissionProfile(duration_hours=duration_hours, ground_temp_c=ground_temp_c)
    elif "rapid" in name_lower or "dash" in name_lower or "response" in name_lower:
        return RapidResponseMissionProfile(duration_hours=duration_hours, ground_temp_c=ground_temp_c)
    else: # Default endurance
        return EnduranceMissionProfile(duration_hours=duration_hours, ground_temp_c=ground_temp_c)

__all__ = [
    "EnduranceMissionProfile",
    "HotWeatherMissionProfile",
    "HighAltitudeMissionProfile",
    "RapidResponseMissionProfile",
    "get_mission_profile"
]
