import asyncio

from app.schemas.chat_schema import RagSource
from app.schemas.review_schema import ReviewSource, SpecialistFinding, SpecialistReviewResult
from app.services.retrieval_service import retrieve_sources

NO_DIRECT_EVIDENCE = "The uploaded contract chunks do not directly confirm this item."

DOMAIN_CONFIGS = {
    "deposit_return": {
        "query": "deposit return timing refund delay new tenant lease termination tenant right registration",
        "title": "Deposit return condition requires confirmation",
        "checks": [
            "Check whether the deposit is returned on the contract end date.",
            "Check whether the return is conditional on a new tenant moving in.",
            "Check whether delayed return or tenant right registration should be discussed.",
        ],
        "high_markers": ["new tenant", "move in", "after a new tenant", "신규", "새 임차인", "입주 후"],
        "reason": "If deposit return depends on a new tenant or another uncertain event, repayment may be delayed after lease termination.",
    },
    "special_clause": {
        "query": "special clause unfair tenant burden landlord exemption vague responsibility",
        "title": "Special clause responsibility scope requires confirmation",
        "checks": [
            "Check whether a special clause places excessive responsibility on the tenant.",
            "Check whether the landlord's responsibility is broadly exempted.",
            "Ask for vague responsibility wording to be clarified in writing.",
        ],
        "high_markers": ["all responsibility", "all costs", "any damage", "모든", "전부", "일체"],
        "reason": "Broad or vague special clauses may shift excessive responsibility to the tenant.",
    },
    "repair_cost": {
        "query": "repair cost maintenance restoration tenant burden normal wear aging facility defect",
        "title": "Repair cost and restoration scope requires confirmation",
        "checks": [
            "Separate tenant-caused damage from aging or normal wear.",
            "Check whether major facility defects remain the landlord's responsibility.",
            "Clarify the restoration scope before signing.",
        ],
        "high_markers": ["all repair", "all maintenance", "all restoration", "모든 수리", "전부 부담", "원상복구"],
        "reason": "If repair and restoration responsibility is written too broadly, normal wear or aging facilities may become disputed.",
    },
    "move_in_fixed_date": {
        "query": "move in registration fixed date opposing power priority repayment tenant protection",
        "title": "Move-in registration and fixed date require confirmation",
        "checks": [
            "Check whether move-in registration can be completed immediately.",
            "Check whether a fixed date can be obtained on the contract document.",
            "Confirm the relation to opposing power and priority repayment.",
        ],
        "high_markers": ["cannot register", "no fixed date", "전입 불가", "확정일자 불가"],
        "reason": "Move-in registration and a fixed date are key confirmation items for tenant protection and priority repayment.",
    },
    "registry_check": {
        "query": "registry record mortgage seizure senior rights owner lessor encumbrance",
        "title": "Registry record review requires confirmation",
        "checks": [
            "Check ownership and whether the lessor matches the registered owner.",
            "Check mortgage, seizure, and senior rights.",
            "Review whether the deposit amount is reasonable compared with prior secured rights.",
        ],
        "high_markers": ["mortgage", "seizure", "senior lien", "근저당", "압류", "선순위"],
        "reason": "Senior rights or encumbrances in the registry may affect deposit recovery risk.",
    },
    "jeonse_fraud_prevention": {
        "query": "jeonse fraud prevention guarantee insurance market price landlord tax arrears checklist",
        "title": "Jeonse fraud prevention checklist requires confirmation",
        "checks": [
            "Check market price and deposit ratio.",
            "Check guarantee insurance availability.",
            "Check landlord identity, tax arrears, and licensed agent information.",
        ],
        "high_markers": ["tax arrears", "guarantee insurance unavailable", "시세", "보증보험", "체납"],
        "reason": "Jeonse fraud prevention requires multiple checks beyond the contract text, including price, insurance, and landlord information.",
    },
    "standard_contract": {
        "query": "standard lease contract missing required item clause responsibility checklist",
        "title": "Standard contract item review requires confirmation",
        "checks": [
            "Check whether required contract items are omitted.",
            "Compare special clauses with standard contract expectations.",
            "Confirm whether important responsibilities are clearly allocated.",
        ],
        "high_markers": ["missing", "omitted", "누락", "빈칸"],
        "reason": "Missing or non-standard clauses may make later interpretation difficult.",
    },
}


def review_domain(domain: str, anonymous_session_id: str, contract_id: int) -> SpecialistReviewResult:
    config = DOMAIN_CONFIGS[domain]
    sources = retrieve_sources(
        message=config["query"],
        rewritten_query=config["query"],
        anonymous_session_id=anonymous_session_id,
        contract_id=contract_id,
    )
    contract_sources = [source for source in sources if source.sourceType == "contract"]
    reference_sources = [source for source in sources if source.sourceType != "contract"]

    finding = SpecialistFinding(
        category=domain,
        riskLevel=_risk_level(config, contract_sources),
        title=config["title"],
        contractEvidence=_contract_evidence(contract_sources),
        relatedSources=[_to_review_source(source) for source in reference_sources[:3]],
        reason=_reason(config, contract_sources),
        recommendations=config["checks"],
    )
    return SpecialistReviewResult(domain=domain, findings=[finding])


async def review_domain_async(domain: str, anonymous_session_id: str, contract_id: int) -> SpecialistReviewResult:
    return await asyncio.to_thread(review_domain, domain, anonymous_session_id, contract_id)


def _risk_level(config: dict, contract_sources: list[RagSource]) -> str:
    if not contract_sources:
        return "LOW"
    joined_contract_text = " ".join(source.chunkText.lower() for source in contract_sources if source.chunkText)
    if any(marker.lower() in joined_contract_text for marker in config["high_markers"]):
        return "HIGH"
    return "CAUTION"


def _contract_evidence(contract_sources: list[RagSource]) -> str:
    if not contract_sources:
        return NO_DIRECT_EVIDENCE
    evidence = contract_sources[0].chunkText.strip()
    return evidence[:500] + ("..." if len(evidence) > 500 else "")


def _reason(config: dict, contract_sources: list[RagSource]) -> str:
    if not contract_sources:
        return "This domain should still be checked, but the current contract chunks do not directly confirm the related clause."
    return config["reason"]


def _to_review_source(source: RagSource) -> ReviewSource:
    return ReviewSource(
        sourceType=source.sourceType,
        sourceTitle=source.sourceTitle,
        chunkText=source.chunkText,
        similarityScore=source.similarityScore,
    )
