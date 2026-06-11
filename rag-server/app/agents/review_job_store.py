from threading import Lock
from uuid import uuid4

from app.schemas.review_schema import ContractReviewJobStatusResponse, ContractReviewRequest, ContractReviewResponse

PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"

_JOBS: dict[str, dict] = {}
_LOCK = Lock()


def create_review_job(_: ContractReviewRequest) -> ContractReviewJobStatusResponse:
    job_id = f"review-job-{uuid4()}"
    job = {
        "jobId": job_id,
        "status": PENDING,
        "progress": 0,
        "result": None,
        "error": None,
    }
    with _LOCK:
        _JOBS[job_id] = job
    return ContractReviewJobStatusResponse(**job)


def get_review_job(job_id: str) -> ContractReviewJobStatusResponse | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        return ContractReviewJobStatusResponse(**job)


def mark_running(job_id: str, progress: int = 10) -> None:
    update_review_job(job_id, status=RUNNING, progress=progress, error=None)


def update_progress(job_id: str, progress: int) -> None:
    update_review_job(job_id, progress=progress)


def mark_completed(job_id: str, result: ContractReviewResponse) -> None:
    update_review_job(job_id, status=COMPLETED, progress=100, result=result, error=None)


def mark_failed(job_id: str, error: str) -> None:
    update_review_job(job_id, status=FAILED, error=error)


def update_review_job(
    job_id: str,
    status: str | None = None,
    progress: int | None = None,
    result: ContractReviewResponse | None = None,
    error: str | None = None,
) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = max(0, min(100, progress))
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
