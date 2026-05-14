from fastapi import APIRouter

from app.schemas.contract_schema import ContractIndexRequest, ContractIndexResponse

router = APIRouter(prefix="/rag/contracts", tags=["contracts"])


@router.post("/index", response_model=ContractIndexResponse)
def index_contract(request: ContractIndexRequest) -> ContractIndexResponse:
    return ContractIndexResponse(
        contractId=request.contractId,
        status="READY_TO_IMPLEMENT",
        analysis={
            "overallRiskLevel": "CAUTION",
            "summary": "계약서 분석 기능 구현 전 기본 응답입니다.",
            "riskItems": [],
        },
    )
