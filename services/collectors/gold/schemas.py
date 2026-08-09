from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ZoneGeographyFeatures(BaseModel):
    """
    Canonical Gold Contract: zone_geography_features
    Represents static geographic context derived from OSM.
    """
    h3_index: str = Field(..., description="H3 resolution 9 index string")
    zone_type: str = Field(..., description="Classification: residential, commercial, mixed, industrial")
    commercial_poi_density: float = Field(..., description="POIs per sq km")
    restaurant_density: float = Field(..., description="Food venues per sq km")
    grocery_density: float = Field(..., description="Supermarkets/convenience per sq km")
    last_updated: datetime

class ZoneNetworkFeatures(BaseModel):
    """
    Canonical Gold Contract: zone_network_features
    Represents road network topology and traffic characteristics.
    """
    h3_index: str = Field(..., description="H3 resolution 9 index string")
    road_density_km_per_sqkm: float
    intersection_density: float
    network_connectivity_index: float
    avg_speed_kph: Optional[float] = Field(None, description="Current live speed if available, null otherwise")
    historical_congestion_ratio: Optional[float] = Field(None, description="Historical vs Free-flow ratio")
    last_updated: datetime

class FacilityCandidateFeatures(BaseModel):
    """
    Canonical Gold Contract: facility_candidate_features
    Represents candidate sites for shadow operations or facility optimization.
    """
    candidate_id: str
    lat: float
    lon: float
    h3_index: str
    zoning_compatibility_score: float
    distance_to_major_arterial_m: float
    competitor_proximity_m: Optional[float]
    last_updated: datetime
