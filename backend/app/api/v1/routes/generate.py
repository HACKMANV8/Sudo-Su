from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ....services.job_manager import InMemoryJobManager, JobStatus


router = APIRouter()
job_manager = InMemoryJobManager.shared()


class GenerateRequest(BaseModel):
    schema: Dict[str, Any]
    mode: str = "generate"
    target_rows: int | None = None
    seed: int | str | None = None
    notify_webhook: str | None = None
    options: Dict[str, Any] | None = None


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def post_generate(req: GenerateRequest) -> dict:
    job_id = str(uuid.uuid4())
    job_manager.create_job(job_id=job_id, user_id="dev", job_type="generate", params=req.dict())
    # For tests, mark as PENDING immediately; a worker would process it
    return {"job_id": job_id, "status": JobStatus.PENDING, "message": "Job queued"}


