import re

from app.schemas.contract_schema import ContractAnalysis, RiskItem

MAX_EVIDENCE_LENGTH = 300

RULES = [
    {
        "category": "DEPOSIT_RETURN",
        "keywords": [
            "보증금",
            "반환",
            "돌려",
            "deposit",
            "return",
            "refund",
            "security deposit",
            "bojeung",
            "보증금",
            "반환",
        ],
        "title": "보증금 반환 조건 확인 필요",
        "description": (
            "보증금을 언제, 어떤 조건에서 돌려받는지 불명확하면 계약 종료 시 분쟁이 생길 수 있습니다. "
            "반환 시점, 공제 가능 항목, 주택 인도와 동시 이행 여부를 임대인 또는 공인중개사에게 확인하세요."
        ),
    },
    {
        "category": "SPECIAL_TERMS",
        "keywords": [
            "특약",
            "별도 합의",
            "임차인 부담",
            "special",
            "clause",
            "addendum",
            "특약",
        ],
        "title": "특약 조항 책임 범위 확인 필요",
        "description": (
            "특약은 계약 당사자 사이의 추가 약속이라 실제 부담 범위에 큰 영향을 줄 수 있습니다. "
            "임차인에게 과도한 책임을 지우거나 보증금 반환을 불명확하게 만드는 표현이 없는지 확인하세요."
        ),
    },
    {
        "category": "REPAIR",
        "keywords": [
            "수리",
            "수선",
            "보수",
            "원상복구",
            "파손",
            "repair",
            "maintenance",
            "damage",
            "fix",
            "수리",
            "보수",
        ],
        "title": "수리비 부담 범위 확인 필요",
        "description": (
            "수리비와 원상복구 범위가 넓게 쓰이면 노후 설비나 통상 손모까지 임차인이 부담하는지 다툼이 생길 수 있습니다. "
            "임대인 부담 수선과 임차인 부담 수선이 어떻게 나뉘는지 확인하세요."
        ),
    },
    {
        "category": "TERMINATION",
        "keywords": [
            "해지",
            "해제",
            "종료",
            "위약금",
            "termination",
            "cancel",
            "end of lease",
            "terminate",
            "해지",
            "종료",
        ],
        "title": "계약 해지 조건 확인 필요",
        "description": (
            "계약 해지나 종료 조건이 불명확하면 중도 해지, 위약금, 보증금 반환 시점에서 분쟁이 생길 수 있습니다. "
            "통지 기한, 위약금, 계약 종료 후 정산 절차를 확인하세요."
        ),
    },
    {
        "category": "MANAGEMENT_FEE",
        "keywords": [
            "관리비",
            "공과금",
            "청소비",
            "maintenance fee",
            "management fee",
            "fee",
            "관리비",
        ],
        "title": "관리비 항목 확인 필요",
        "description": (
            "관리비 항목과 금액 산정 방식이 불명확하면 계약 후 예상하지 못한 비용이 발생할 수 있습니다. "
            "월 관리비에 포함되는 항목, 별도 부과 항목, 정산 방식을 확인하세요."
        ),
    },
]


def analyze_contract(text: str) -> ContractAnalysis:
    sentences = _split_sentences(text)
    lowered_text = text.lower()
    risk_items: list[RiskItem] = []

    for rule in RULES:
        matched_keyword = next((keyword for keyword in rule["keywords"] if keyword.lower() in lowered_text), None)
        if not matched_keyword:
            continue

        risk_items.append(
            RiskItem(
                category=rule["category"],
                riskLevel="CAUTION",
                title=rule["title"],
                description=rule["description"],
                evidence=_find_evidence(sentences, text, matched_keyword),
            )
        )

    if not risk_items:
        return ContractAnalysis(
            overallRiskLevel="SAFE",
            summary=(
                "업로드한 계약서에서 현재 MVP 규칙으로는 주요 위험 키워드가 뚜렷하게 발견되지 않았습니다. "
                "다만 이는 최종 법률 판단이 아니며, 보증금 반환 조건과 특약 조항 등 핵심 항목은 직접 확인하는 것이 좋습니다."
            ),
            riskItems=[],
        )

    matched_titles = ", ".join(item.title for item in risk_items)
    return ContractAnalysis(
        overallRiskLevel="CAUTION",
        summary=(
            f"업로드한 계약서에서 {matched_titles} 항목이 발견되었습니다. "
            "각 항목의 실제 문구를 확인하고, 조건이 불명확한 부분은 임대인 또는 공인중개사에게 명확히 확인하는 것이 좋습니다."
        ),
        riskItems=risk_items,
    )


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    rough_sentences = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    sentences = [re.sub(r"\s+", " ", sentence).strip() for sentence in rough_sentences if sentence.strip()]
    if len(sentences) <= 1:
        sentences = [part.strip() for part in re.split(r"\s{2,}|(?<=다\.)\s*", normalized) if part.strip()]
    return sentences or [normalized]


def _find_evidence(sentences: list[str], full_text: str, keyword: str) -> str:
    lowered_keyword = keyword.lower()

    for index, sentence in enumerate(sentences):
        if lowered_keyword in sentence.lower():
            start = max(0, index - 1)
            end = min(len(sentences), index + 2)
            return _truncate_evidence(" ".join(sentences[start:end]))

    lowered_text = full_text.lower()
    position = lowered_text.find(lowered_keyword)
    if position >= 0:
        start = max(0, position - 120)
        end = min(len(full_text), position + len(keyword) + 180)
        return _truncate_evidence(full_text[start:end])

    return "계약서에서 관련 표현이 발견되었지만, 표시할 문맥을 추출하지 못했습니다."


def _truncate_evidence(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= MAX_EVIDENCE_LENGTH:
        return compact
    return compact[:MAX_EVIDENCE_LENGTH].rstrip() + "..."
