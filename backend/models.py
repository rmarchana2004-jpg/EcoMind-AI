from pydantic import BaseModel
from typing import Optional


class EnvironmentalData(BaseModel):

    # Soil
    soil_ph: Optional[float] = None
    organic_carbon: Optional[float] = None
    soil_moisture: Optional[float] = None

    # Climate
    temperature: Optional[float] = None
    rainfall: Optional[float] = None

    # Land
    land_use: Optional[str] = None

    # Biodiversity
    species_richness: Optional[int] = None
    habitat_diversity: Optional[float] = None

    # Human impact
    pollution_level: Optional[str] = None
    deforestation_level: Optional[str] = None

    # Location
    region: Optional[str] = None


class ChatRequest(BaseModel):

    message: str

    session_id: str = "demo-session"

    environment: Optional[EnvironmentalData] = None