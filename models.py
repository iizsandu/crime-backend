from pydantic import BaseModel

class CrimeReport(BaseModel):
    title: str
    crime_type: str
    description: str
    location: str
    date: str
    time: str

class CommuteRequest(BaseModel):
    location_origin: str
    location_destination: str

