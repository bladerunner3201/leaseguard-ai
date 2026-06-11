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

## 10. Async Review Job API

The async review API starts multi-agent report generation as a background job and returns a `jobId` immediately.
The current implementation uses an in-memory FastAPI job store, so job state disappears when the FastAPI process restarts.
The response schema is kept explicit so it can later be moved to Spring Boot and MySQL persistence.

### 10.1 Create Review Job

```powershell
$JobStart = Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/review-jobs" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = $SessionId
    contractId = $ContractId
    documentName = "sample_lease_contract.txt"
  } | ConvertTo-Json -Depth 10)

$JobId = $JobStart.jobId
$JobStart
```

Expected:

```json
{
  "jobId": "review-job-uuid",
  "status": "PENDING",
  "message": "Multi-agent review job started."
}
```

### 10.2 Poll Job Status

```powershell
do {
  Start-Sleep -Seconds 2
  $JobStatus = Invoke-RestMethod `
    -Method Get `
    -Uri "$RagBaseUrl/rag/contracts/review-jobs/$JobId"

  "status=$($JobStatus.status), progress=$($JobStatus.progress)"
} while ($JobStatus.status -eq "PENDING" -or $JobStatus.status -eq "RUNNING")

$JobStatus.status
$JobStatus.progress
$JobStatus.result.overallRiskLevel
$JobStatus.result.summary
$JobStatus.result.reportMarkdown
$JobStatus.error
```

Expected progress values are updated by stage:

| Progress | Stage |
| --- | --- |
| 10 | Job started |
| 25 | Supervisor completed |
| 50 | Specialist review completed |
| 75 | Risk aggregation completed |
| 90 | Report writing |
| 100 | Completed |

### 10.3 Completed Result Shape

```json
{
  "jobId": "review-job-uuid",
  "status": "COMPLETED",
  "progress": 100,
  "result": {
    "overallRiskLevel": "CAUTION",
    "summary": "...",
    "agentResults": {},
    "reportMarkdown": "...",
    "sources": []
  },
  "error": null
}
```

### 10.4 Failure Case: Contract Not Indexed

```powershell
$FailedJobStart = Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/review-jobs" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = "missing-session"
    contractId = 999999
    documentName = "missing_contract.txt"
  } | ConvertTo-Json -Depth 10)

$FailedJobId = $FailedJobStart.jobId
Start-Sleep -Seconds 2

Invoke-RestMethod `
  -Method Get `
  -Uri "$RagBaseUrl/rag/contracts/review-jobs/$FailedJobId"
```

Expected:

- `status` is `FAILED`.
- `error` contains `계약서가 인덱싱되지 않았거나 검색 가능한 chunk가 없습니다.`

### 10.5 Sync Review vs Async Review

| API | Behavior | Use Case |
| --- | --- | --- |
| `POST /rag/contracts/review` | Waits until the full report is generated and returns the result in the same response. | Direct FastAPI testing or small reports. |
| `POST /rag/contracts/review-jobs` | Starts background report generation and returns `jobId` immediately. | Long-running multi-agent review flows. |
| `GET /rag/contracts/review-jobs/{jobId}` | Polls status, progress, result, and error. | Frontend or backend polling integration. |

## 11. Validation Commands

```powershell
cd rag-server
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```
