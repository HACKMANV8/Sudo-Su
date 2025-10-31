from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ....services.job_manager import InMemoryJobManager


router = APIRouter()
job_manager = InMemoryJobManager.shared()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job

@router.get("/jobs")
async def list_jobs() -> dict:
    return {"jobs": job_manager.list_jobs()}


