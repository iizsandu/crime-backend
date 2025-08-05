from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import CrimeReport
from app.utils.database import crime_collection, report_collection
from bson import ObjectId

router = APIRouter()

@router.post("/report")
def report_crime(crime: CrimeReport):
    document = {
        "title": crime.title,
        "crime_type": crime.crime_type,
        "description": crime.description,
        "location": crime.location,
        "date": crime.date, 
        "time": crime.time
    }
    result = report_collection.insert_one(document)
    if result.inserted_id:
        return {"message": "Crime report submitted successfully", "id": str(result.inserted_id)}
    raise HTTPException(status_code=500, detail="Failed to submit crime report")
