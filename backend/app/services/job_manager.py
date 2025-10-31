from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class JobStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class Job:
    id: str
    user_id: str
    type: str
    status: str = JobStatus.PENDING
    params: Dict[str, Any] = field(default_factory=dict)
    generation_report: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    realism: Optional[Dict[str, Any]] = None
    csv_s3_key: Optional[str] = None
    fingerprint: Optional[str] = None


class InMemoryJobManager:
    _shared: "InMemoryJobManager" | None = None

    @classmethod
    def shared(cls) -> "InMemoryJobManager":
        if not cls._shared:
            cls._shared = InMemoryJobManager()
        return cls._shared

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def create_job(self, job_id: str, user_id: str, job_type: str, params: Dict[str, Any]) -> None:
        self._jobs[job_id] = Job(id=job_id, user_id=user_id, type=job_type, params=params)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        return None if not job else job.__dict__

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [j.__dict__ for j in self._jobs.values()]


