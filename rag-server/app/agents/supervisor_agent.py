from app.agents.advisor_report_agent import build_report
from app.agents.risk_aggregator_agent import aggregate_risks
from app.agents.specialist_review_agent import review_domain
from app.schemas.review_schema import ContractReviewRequest, ContractReviewResponse, SupervisorResult

REVIEW_DOMAINS = [
    "deposit_return",
    "special_clause",
    "repair_cost",
    "move_in_fixed_date",
    "registry_check",
    "jeonse_fraud_prevention",
    "standard_contract",
]


def plan_review(_: ContractReviewRequest) -> SupervisorResult:
    return SupervisorResult(
        taskType="contract_review_report",
        selectedDomains=list(REVIEW_DOMAINS),
    )


def run_contract_review(request: ContractReviewRequest) -> ContractReviewResponse:
    supervisor = plan_review(request)

    # The domain function boundary is intentionally small so it can later be
    # executed with asyncio.gather or worker pools without changing schemas.
    specialist_reviews = [
        review_domain(
            domain=domain,
            anonymous_session_id=request.anonymousSessionId,
            contract_id=request.contractId,
        )
        for domain in supervisor.selectedDomains
    ]

    aggregated_risk = aggregate_risks(specialist_reviews)
    report_markdown = build_report(aggregated_risk, request.documentName)
    sources = collect_sources(specialist_reviews)

    return ContractReviewResponse(
        overallRiskLevel=aggregated_risk.overallRiskLevel,
        summary=aggregated_risk.summary,
        agentResults={
            "supervisor": supervisor,
            "specialistReviews": specialist_reviews,
            "aggregatedRisk": aggregated_risk,
        },
        reportMarkdown=report_markdown,
        sources=sources,
    )


def collect_sources(specialist_reviews):
    seen: set[tuple[str, str, str]] = set()
    sources = []
    for review in specialist_reviews:
        for finding in review.findings:
            for source in finding.relatedSources:
                key = (source.sourceType, source.sourceTitle, source.chunkText[:120])
                if key in seen:
                    continue
                seen.add(key)
                sources.append(source)
    return sources[:20]


def _collect_sources(specialist_reviews):
    return collect_sources(specialist_reviews)
