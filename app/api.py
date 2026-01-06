from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict
import logging

from app.pipeline.runner import run_pipeline
from app.pipeline.steps import dashboard, PipelineConfig
from app.db.database import get_connection

app = FastAPI(
    title="Owner Intelligence API",
    description="API for oil & gas mineral acquisition workflows",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
    sample_dir: str = "app/sample_data"


@app.get("/")
async def root():
    return {
        "message": "Owner Intelligence API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/pipeline/run")
async def run_pipeline_endpoint(request: PipelineRequest):
    """Run the complete pipeline"""
    try:
        sample_dir = Path(request.sample_dir)
        if not sample_dir.exists():
            raise HTTPException(status_code=400, detail="Sample directory not found")
        
        run_pipeline(sample_dir)
        return {"status": "success", "message": "Pipeline completed successfully"}
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard")
async def get_dashboard():
    """Get pipeline dashboard metrics"""
    try:
        config = PipelineConfig()
        results = dashboard(config)
        return {
            "source_records": results.source_records,
            "owner_count": results.owner_count,
            "addresses": results.addresses,
            "contacts": results.contacts,
            "outreach_queued": results.outreach_queued,
            "deliverable_addresses": results.deliverable_addresses,
            "mobile_confirmed": results.mobile_confirmed,
            "daily_hot_leads": results.daily_hot_leads
        }
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/owners")
async def get_owners():
    """Get list of all owners"""
    try:
        with get_connection() as conn:
            owners = conn.execute("SELECT * FROM owners").fetchall()
            return {"owners": [dict(row) for row in owners]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hot-leads")
async def get_hot_leads():
    """Get list of hot leads"""
    try:
        with get_connection() as conn:
            leads = conn.execute("SELECT * FROM hot_leads").fetchall()
            return {"hot_leads": [dict(row) for row in leads]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
