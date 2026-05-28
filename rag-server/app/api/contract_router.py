from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas.contract_schema import ContractIndexRequest, ContractIndexResponse
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
