import asyncio

from app.agents.advisor_report_agent import build_report
from app.agents.risk_aggregator_agent import aggregate_risks
from app.agents.review_job_store import mark_completed, mark_failed, mark_running, update_progress
from app.agents.specialist_review_agent import review_domain_async
from app.agents.supervisor_agent import collect_sources, plan_review
from app.schemas.review_schema import AgentResults, ContractReviewRequest, ContractReviewResponse
from app.vectorstore.chroma_client import get_user_contracts_collection

NO_CONTRACT_CHUNKS_ERROR = "계약서가 인덱싱되지 않았거나 검색 가능한 chunk가 없습니다."


def run_review_job(job_id: str, request: ContractReviewRequest) -> None:
    try:
        asyncio.run(_run_review_job_async(job_id, request))
    except Exception as exception:
        mark_failed(job_id, str(exception))


async def _run_review_job_async(job_id: str, request: ContractReviewRequest) -> None:
    mark_running(job_id, progress=10)
    await asyncio.to_thread(_ensure_contract_chunks, request.anonymousSessionId, request.contractId)

    supervisor = plan_review(request)
    update_progress(job_id, 25)

    specialist_reviews = await asyncio.gather(
        *[
            review_domain_async(
                domain=domain,
                anonymous_session_id=request.anonymousSessionId,
                contract_id=request.contractId,
            )
            for domain in supervisor.selectedDomains
        ]
    )
    update_progress(job_id, 50)

    aggregated_risk = aggregate_risks(specialist_reviews)
    update_progress(job_id, 75)

    update_progress(job_id, 90)
    report_markdown = await asyncio.to_thread(build_report, aggregated_risk, request.documentName)
    sources = collect_sources(specialist_reviews)

    result = ContractReviewResponse(
        overallRiskLevel=aggregated_risk.overallRiskLevel,
        summary=aggregated_risk.summary,
        agentResults=AgentResults(
            supervisor=supervisor,
            specialistReviews=specialist_reviews,
            aggregatedRisk=aggregated_risk,
        ),
        reportMarkdown=report_markdown,
        sources=sources,
    )
    mark_completed(job_id, result)


def _ensure_contract_chunks(anonymous_session_id: str, contract_id: int) -> None:
    collection = get_user_contracts_collection()
    result = collection.get(
        where={
            "$and": [
                {"anonymousSessionId": anonymous_session_id},
                {"contractId": contract_id},
            ]
        },
        limit=1,
        include=["documents"],
    )
    if not result.get("documents"):
        raise ValueError(NO_CONTRACT_CHUNKS_ERROR)
