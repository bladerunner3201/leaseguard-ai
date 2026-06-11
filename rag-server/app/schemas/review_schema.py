from pydantic import BaseModel, Field


class ContractReviewRequest(BaseModel):
    anonymousSessionId: str
    contractId: int
    documentName: str | None = None


class ReviewSource(BaseModel):
    sourceType: str
    sourceTitle: str
    chunkText: str
    similarityScore: float | None = None


class SpecialistFinding(BaseModel):
    category: str
    riskLevel: str
    title: str
    contractEvidence: str
    relatedSources: list[ReviewSource] = Field(default_factory=list)
    reason: str
    recommendations: list[str] = Field(default_factory=list)


class SpecialistReviewResult(BaseModel):
    agentName: str = "SpecialistReviewAgent"
    domain: str
    findings: list[SpecialistFinding] = Field(default_factory=list)


class SupervisorResult(BaseModel):
    agentName: str = "SupervisorAgent"
    taskType: str
    selectedDomains: list[str]


class AggregatedRiskResult(BaseModel):
    agentName: str = "RiskAggregatorAgent"
    overallRiskLevel: str
    summary: str
    topRisks: list[SpecialistFinding] = Field(default_factory=list)
    domainResults: list[SpecialistReviewResult] = Field(default_factory=list)


class AgentResults(BaseModel):
    supervisor: SupervisorResult
    specialistReviews: list[SpecialistReviewResult]
    aggregatedRisk: AggregatedRiskResult


class ContractReviewResponse(BaseModel):
    overallRiskLevel: str
    summary: str
    agentResults: AgentResults
    reportMarkdown: str
    sources: list[ReviewSource] = Field(default_factory=list)
