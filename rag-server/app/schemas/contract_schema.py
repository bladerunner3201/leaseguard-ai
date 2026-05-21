from pydantic import BaseModel


class ContractIndexRequest(BaseModel):
    anonymousSessionId: str
    contractId: int
    filePath: str
    originalFileName: str


class RiskItem(BaseModel):
    category: str
    riskLevel: str
    title: str
    description: str
    evidence: str


class ContractAnalysis(BaseModel):
    overallRiskLevel: str
    summary: str
    riskItems: list[RiskItem]


class ContractIndexResponse(BaseModel):
    contractId: int
    status: str
    analysis: ContractAnalysis
