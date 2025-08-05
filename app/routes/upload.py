from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def upload_placeholder():
    return {"message": "Upload route is under construction"}