import asyncio

from app.schemas.chat_schema import RagSource
from app.schemas.review_schema import ReviewSource, SpecialistFinding, SpecialistReviewResult
from app.services.retrieval_service import retrieve_sources

NO_DIRECT_EVIDENCE = "업로드된 계약서 조각만으로는 이 항목을 직접 확인하기 어렵습니다."

DOMAIN_CONFIGS = {
    "deposit_return": {
        "query": "deposit return timing refund delay new tenant lease termination tenant right registration",
        "title": "보증금 반환 조건 확인 필요",
        "checks": [
            "보증금이 계약 종료일에 반환되는지 확인하세요.",
            "보증금 반환이 신규 임차인 입주 같은 조건에 묶여 있는지 확인하세요.",
            "반환 지연 시 대응 방법과 임차권등기명령 필요성을 상담할 수 있는지 확인하세요.",
        ],
        "high_markers": ["new tenant", "move in", "after a new tenant", "신규", "새 임차인", "입주 후"],
        "reason": "보증금 반환이 신규 임차인 입주 등 불확실한 조건에 연결되어 있으면 계약 종료 후 반환이 지연될 수 있습니다.",
    },
    "special_clause": {
        "query": "special clause unfair tenant burden landlord exemption vague responsibility",
        "title": "특약 조항 책임 범위 확인 필요",
        "checks": [
            "특약이 임차인에게 과도한 책임을 지우는지 확인하세요.",
            "임대인의 책임을 지나치게 넓게 면제하는 표현이 있는지 확인하세요.",
            "모호한 책임 문구는 계약 전 서면으로 구체화해 달라고 요청하세요.",
        ],
        "high_markers": ["all responsibility", "all costs", "any damage", "모든", "전부", "일체"],
        "reason": "넓고 모호한 특약은 임차인에게 예상보다 큰 책임을 전가할 수 있습니다.",
    },
    "repair_cost": {
        "query": "repair cost maintenance restoration tenant burden normal wear aging facility defect",
        "title": "수리비와 원상복구 범위 확인 필요",
        "checks": [
            "임차인의 고의 또는 과실로 생긴 손상과 노후화 또는 통상 사용에 따른 손상을 구분하세요.",
            "주요 설비 하자와 노후 설비 수리가 임대인 책임으로 남는지 확인하세요.",
            "원상복구 범위를 계약 전 구체적으로 확인하세요.",
        ],
        "high_markers": ["all repair", "all maintenance", "all restoration", "모든 수리", "전부 부담", "원상복구"],
        "reason": "수리와 원상복구 책임이 너무 넓게 쓰이면 노후 설비나 통상 사용으로 인한 손상까지 분쟁이 될 수 있습니다.",
    },
    "move_in_fixed_date": {
        "query": "move in registration fixed date opposing power priority repayment tenant protection",
        "title": "전입신고와 확정일자 확인 필요",
        "checks": [
            "입주 후 즉시 전입신고가 가능한지 확인하세요.",
            "계약서에 확정일자를 받을 수 있는지 확인하세요.",
            "대항력과 우선변제권 확보에 필요한 절차를 확인하세요.",
        ],
        "high_markers": ["cannot register", "no fixed date", "전입 불가", "확정일자 불가"],
        "reason": "전입신고와 확정일자는 임차인의 권리 보호와 보증금 회수 가능성에 중요한 확인 항목입니다.",
    },
    "registry_check": {
        "query": "registry record mortgage seizure senior rights owner lessor encumbrance",
        "title": "등기부등본 권리관계 확인 필요",
        "checks": [
            "임대인이 등기부상 소유자와 일치하는지 확인하세요.",
            "근저당, 압류, 선순위 권리 등이 있는지 확인하세요.",
            "보증금 규모가 선순위 권리와 비교해 과도하지 않은지 검토하세요.",
        ],
        "high_markers": ["mortgage", "seizure", "senior lien", "근저당", "압류", "선순위"],
        "reason": "등기부상 선순위 권리나 제한사항은 보증금 회수 위험에 영향을 줄 수 있습니다.",
    },
    "jeonse_fraud_prevention": {
        "query": "jeonse fraud prevention guarantee insurance market price landlord tax arrears checklist",
        "title": "전세사기 예방 체크리스트 확인 필요",
        "checks": [
            "시세와 보증금 비율을 확인하세요.",
            "보증보험 가입 가능성을 확인하세요.",
            "임대인 신원, 세금 체납 여부, 공인중개사 정보를 확인하세요.",
        ],
        "high_markers": ["tax arrears", "guarantee insurance unavailable", "시세", "보증보험", "체납"],
        "reason": "전세사기 예방은 계약서 문구 외에도 시세, 보증보험, 임대인 정보 등 여러 항목을 함께 확인해야 합니다.",
    },
    "standard_contract": {
        "query": "standard lease contract missing required item clause responsibility checklist",
        "title": "표준계약서 필수 항목 확인 필요",
        "checks": [
            "계약서 필수 기재 항목이 빠져 있는지 확인하세요.",
            "특약이 표준계약서의 기본 책임 배분과 충돌하는지 확인하세요.",
            "중요 책임이 명확하게 배분되어 있는지 확인하세요.",
        ],
        "high_markers": ["missing", "omitted", "누락", "빈칸"],
        "reason": "필수 항목이 빠지거나 비표준적인 문구가 있으면 나중에 해석이 어려워질 수 있습니다.",
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
        return "이 영역은 확인이 필요하지만, 현재 계약서 조각에서는 관련 조항을 직접 확인하기 어렵습니다."
    return config["reason"]


def _to_review_source(source: RagSource) -> ReviewSource:
    return ReviewSource(
        sourceType=source.sourceType,
        sourceTitle=source.sourceTitle,
        chunkText=source.chunkText,
        similarityScore=source.similarityScore,
    )
