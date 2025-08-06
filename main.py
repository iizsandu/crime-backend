from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import commute, report, upload

app = FastAPI(
    title="Crime-Aware Safety Platform",
    description="Backend API for crime reporting, uploads, and crime-aware routing",
    version="1.0.0"
)

# origins = ['http://localhost:3000']
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(commute.router, prefix="/commute", tags=["Crime-Awareness Routing"])
app.include_router(report.router, prefix="/report", tags=["Crime Reporting"])
app.include_router(upload.router, prefix="/upload", tags=["Upload Image"])

@app.get("/")
def root():
    return {"message": "Welcome to the Crime-Awareness Safety Platform API"}

