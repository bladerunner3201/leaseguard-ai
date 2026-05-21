from fastapi import APIRouter

from app.schemas.contract_schema import ContractAnalysis, ContractIndexRequest, ContractIndexResponse, RiskItem

router = APIRouter(prefix="/rag/contracts", tags=["contracts"])


@router.post("/index", response_model=ContractIndexResponse)
def index_contract(request: ContractIndexRequest) -> ContractIndexResponse:
    return ContractIndexResponse(
        contractId=request.contractId,
        status="INDEXED",
        analysis=ContractAnalysis(
            overallRiskLevel="CAUTION",
            summary=(
                "This is a fixed stub analysis response for Spring Boot integration testing. "
                "Deposit return terms and special clauses should be checked again when real RAG is implemented."
            ),
            riskItems=[
                RiskItem(
                    category="DEPOSIT_RETURN",
                    riskLevel="CAUTION",
                    title="Deposit return terms need review",
                    description=(
                        "This is a sample risk item returned by the stub server. "
                        "It is not a real contract analysis result and is only for testing the Spring Boot save flow."
                    ),
                    evidence="stub evidence: uploaded contract file was received",
                ),
                RiskItem(
                    category="SPECIAL_TERMS",
                    riskLevel="CAUTION",
                    title="Special clause scope needs review",
                    description="The real RAG implementation should check whether the special clause scope is too broad.",
                    evidence="stub evidence",
                ),
            ],
        ),
    )
