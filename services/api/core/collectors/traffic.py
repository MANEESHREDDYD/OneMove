from pydantic import BaseModel


class TrafficData(BaseModel):
    congestion_level: str
    travel_time_seconds: int
    source: str

class TrafficProvider:
    def __init__(self, mode: str = "DISABLED"):
        self.mode = mode

    async def fetch_route_traffic(self, origin: str, dest: str) -> TrafficData:
        """
        Provides traffic data between zones. 
        Currently implemented in DISABLED mode requiring OWNER_DECISION for TomTom keys.
        """
        if self.mode == "DISABLED":
            return TrafficData(
                congestion_level="UNKNOWN",
                travel_time_seconds=0,
                source="DISABLED_STUB"
            )
        
        # Placeholder for TomTom integration
        raise NotImplementedError("TomTom API integration requires OWNER credentials.")
