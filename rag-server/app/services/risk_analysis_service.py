from app.schemas.contract_schema import ContractAnalysis, RiskItem

RULES = [
    {
        "category": "DEPOSIT_RETURN",
        "keywords": ["deposit", "return", "refund", "security deposit", "bojeung", "보증금", "반환"],
        "title": "Deposit return terms found",
        "description": "The contract text contains deposit or return related wording. Review the timing and conditions.",
    },
    {
        "category": "SPECIAL_TERMS",
        "keywords": ["special", "clause", "addendum", "특약"],
        "title": "Special clause wording found",
        "description": "The contract text contains special clause wording. Review whether duties are too broad or unclear.",
    },
    {
        "category": "REPAIR",
        "keywords": ["repair", "maintenance", "damage", "fix", "수리", "보수"],
        "title": "Repair or maintenance wording found",
        "description": "The contract text mentions repair or maintenance. Review who pays and when the duty applies.",
    },
    {
        "category": "TERMINATION",
        "keywords": ["termination", "cancel", "end of lease", "terminate", "해지", "종료"],
        "title": "Termination wording found",
        "description": "The contract text mentions termination. Review notice period, penalties, and return conditions.",
    },
    {
        "category": "MANAGEMENT_FEE",
        "keywords": ["management fee", "maintenance fee", "fee", "관리비"],
        "title": "Management fee wording found",
        "description": "The contract text mentions fees. Review what is included and whether the amount is clear.",
    },
]


def analyze_contract(text: str) -> ContractAnalysis:
    lowered_text = text.lower()
    risk_items: list[RiskItem] = []

    for rule in RULES:
        matched_keyword = next((keyword for keyword in rule["keywords"] if keyword.lower() in lowered_text), None)
        if matched_keyword:
            risk_items.append(
                RiskItem(
                    category=rule["category"],
                    riskLevel="CAUTION",
                    title=rule["title"],
                    description=rule["description"],
                    evidence=f"Rule matched for category: {rule['category']}",
                )
            )

    if not risk_items:
        return ContractAnalysis(
            overallRiskLevel="SAFE",
            summary=(
                "The contract was indexed in ChromaDB. No simple rule keyword was matched. "
                "This is not a legal judgment."
            ),
            riskItems=[],
        )

    return ContractAnalysis(
        overallRiskLevel="CAUTION",
        summary=(
            f"The contract was indexed in ChromaDB and {len(risk_items)} simple rule item(s) were found. "
            "This is a keyword-based MVP check, not legal advice."
        ),
        riskItems=risk_items,
    )
