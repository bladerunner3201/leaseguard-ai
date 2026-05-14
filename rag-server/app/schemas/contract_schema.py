from pydantic import BaseModel


class ContractIndexRequest(BaseModel):
    anonymousSessionId: str
    contractId: int
    filePath: str
    originalFileName: str


class ContractIndexResponse(BaseModel):
    contractId: int
    status: str
    analysis: dict
