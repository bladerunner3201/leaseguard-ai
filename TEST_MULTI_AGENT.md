# Multi-Agent Contract Review Test Commands

This document tests the FastAPI-only Hybrid Multi-Agent contract review pipeline.
It does not require Spring Boot or React integration in this stage.

## 1. Start Infrastructure

```powershell
docker compose up -d mysql chromadb
```

## 2. Start FastAPI

```powershell
cd rag-server
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

## 3. Index Reference Documents

```powershell
$RagBaseUrl = "http://localhost:8000"

Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/references/index"
```

## 4. Index a Sample Contract

```powershell
$SessionId = "multi-agent-test-session"
$ContractId = 91001
$ContractPath = "D:\leaseguard-ai\leaseguard-ai\data\sample_contracts\sample_lease_contract.txt"

Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/index" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = $SessionId
    contractId = $ContractId
    filePath = $ContractPath
    originalFileName = "sample_lease_contract.txt"
  } | ConvertTo-Json -Depth 10)
```

## 5. Call Multi-Agent Review

```powershell
$ReviewResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/review" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = $SessionId
    contractId = $ContractId
    documentName = "sample_lease_contract.txt"
  } | ConvertTo-Json -Depth 10)

$ReviewResponse.overallRiskLevel
$ReviewResponse.summary
$ReviewResponse.agentResults.supervisor.selectedDomains
$ReviewResponse.agentResults.specialistReviews.Count
$ReviewResponse.reportMarkdown
$ReviewResponse.sources.Count
```

## 6. Expected Response Shape

```json
{
  "overallRiskLevel": "CAUTION",
  "summary": "Overall risk level is CAUTION...",
  "agentResults": {
    "supervisor": {
      "agentName": "SupervisorAgent",
      "taskType": "contract_review_report",
      "selectedDomains": [
        "deposit_return",
        "special_clause",
        "repair_cost",
        "move_in_fixed_date",
        "registry_check",
        "jeonse_fraud_prevention",
        "standard_contract"
      ]
    },
    "specialistReviews": [],
    "aggregatedRisk": {}
  },
  "reportMarkdown": "# Multi-Agent Contract Review Report\n...",
  "sources": []
}
```

## 7. OpenAI Enabled Test

When `OPENAI_API_KEY` is configured in `rag-server/.env`, the `AdvisorReportAgent` uses OpenAI Chat API once to generate `reportMarkdown`.
Specialist agents do not call OpenAI.

Check:

```powershell
$ReviewResponse.reportMarkdown.Contains("legal advice")
```

Expected:

- `reportMarkdown` is generated.
- The response includes `overallRiskLevel`, `summary`, `agentResults`, `reportMarkdown`, and `sources`.
- The report includes a caution that it is not legal advice.

## 8. Fallback Test Without OpenAI

Temporarily run FastAPI without `OPENAI_API_KEY`, or set it to an empty value.

Expected:

- `/rag/contracts/review` still returns HTTP 200.
- `reportMarkdown` uses the template fallback report.
- The response shape remains unchanged.

## 9. Existing Chat API Regression Test

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/chat" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = $SessionId
    contractId = $ContractId
    message = "Check whether the deposit return condition is risky."
    chatHistory = @()
  } | ConvertTo-Json -Depth 10)
```

Expected:

- Existing `/rag/chat` still returns `answer` and `sources`.
- Existing `/rag/contracts/index` and `/rag/references/index` behavior remains unchanged.

## 10. Validation Commands

```powershell
cd rag-server
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```
