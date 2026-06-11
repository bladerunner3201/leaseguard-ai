from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException

from app.agents.review_job_runner import run_review_job
from app.agents.review_job_store import create_review_job, get_review_job
from app.agents.supervisor_agent import run_contract_review
from app.schemas.contract_schema import ContractIndexRequest, ContractIndexResponse
from app.schemas.review_schema import (
    ContractReviewJobStartResponse,
    ContractReviewJobStatusResponse,
    ContractReviewRequest,
    ContractReviewResponse,
)
from app.services.contract_indexing_service import index_contract as index_contract_service

router = APIRouter(prefix="/rag/contracts", tags=["contracts"])


@router.post("/index", response_model=ContractIndexResponse)
def index_contract(request: ContractIndexRequest) -> ContractIndexResponse:
    try:
        return index_contract_service(request)
    except FileNotFoundError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception


@router.post("/review", response_model=ContractReviewResponse)
def review_contract(request: ContractReviewRequest) -> ContractReviewResponse:
    try:
        return run_contract_review(request)
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception


@router.post("/review-jobs", response_model=ContractReviewJobStartResponse)
def start_review_job(
    request: ContractReviewRequest,
    background_tasks: BackgroundTasks,
) -> ContractReviewJobStartResponse:
    job = create_review_job(request)
    background_tasks.add_task(run_review_job, job.jobId, request)
    return ContractReviewJobStartResponse(
        jobId=job.jobId,
        status=job.status,
        message="Multi-agent review job started.",
    )


@router.get("/review-jobs/{job_id}", response_model=ContractReviewJobStatusResponse)
def get_review_job_status(job_id: str) -> ContractReviewJobStatusResponse:
    job = get_review_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review job not found.")
    return job
