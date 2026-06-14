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

## 11. Spring Boot Review Job Proxy

Spring Boot exposes the FastAPI async job flow through contract-scoped APIs.
The backend checks the current `X-Anonymous-Session-Id` against the contract owner before calling FastAPI.
Deleted contracts are rejected by the existing contract ownership lookup.

### 11.1 Start Job Through Spring Boot

```powershell
$BackendBaseUrl = "http://localhost:8080"

$SpringJobStart = Invoke-RestMethod `
  -Method Post `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-jobs" `
  -Headers @{ "X-Anonymous-Session-Id" = $SessionId }

$SpringJobId = $SpringJobStart.data.jobId
$SpringJobStart.data
```

### 11.2 Poll Job Through Spring Boot

```powershell
do {
  Start-Sleep -Seconds 2
  $SpringJobStatus = Invoke-RestMethod `
    -Method Get `
    -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-jobs/$SpringJobId" `
    -Headers @{ "X-Anonymous-Session-Id" = $SessionId }

  "status=$($SpringJobStatus.data.status), progress=$($SpringJobStatus.data.progress)"
} while ($SpringJobStatus.data.status -eq "PENDING" -or $SpringJobStatus.data.status -eq "RUNNING")

$SpringJobStatus.data.result.overallRiskLevel
$SpringJobStatus.data.result.summary
$SpringJobStatus.data.result.reportMarkdown
```

### 11.3 Authorization and Deleted Contract Checks

Different anonymous session access should return `403`.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-jobs" `
  -Headers @{ "X-Anonymous-Session-Id" = "other-session-id" }
```

Deleted contract access should return `404` after the contract is soft deleted.

```powershell
Invoke-RestMethod `
  -Method Delete `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId" `
  -Headers @{ "X-Anonymous-Session-Id" = $SessionId }

Invoke-RestMethod `
  -Method Post `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-jobs" `
  -Headers @{ "X-Anonymous-Session-Id" = $SessionId }
```

## 12. React Integration

The analysis result screen includes an `AI 종합 검토 리포트 생성` button.
The UI starts a Spring Boot review job, polls job status, maps numeric progress to user-facing status text, and displays `reportMarkdown` with preserved line breaks.

Progress text mapping:

| Progress | UI Text |
| --- | --- |
| 0-20 | 분석 준비 중 |
| 21-50 | 전문 에이전트 검토 중 |
| 51-75 | 위험도 종합 중 |
| 76-99 | 리포트 작성 중 |
| 100 | 완료 |

The report area displays:

- Overall risk level
- Summary
- Markdown report text
- Source excerpts
- Expandable agent trace

## 13. Current Limitations

- FastAPI review jobs are stored in memory and are used only for in-progress job state.
- Completed multi-agent reports are persisted by Spring Boot in MySQL through `contract_review_reports`.
- Restarting the FastAPI server can remove in-progress job state, but completed reports already saved in MySQL remain available.
- React does not store completed report body, `agentResults`, or `sources` in `localStorage`.
- React stores only `anonymousSessionId`, contract-specific `chatSessionId`, and in-progress `reviewJobId`.

## 14. Persistent Review Report Flow

Completed reports use Spring Boot/MySQL as the source of truth.

Flow:

1. React calls `POST /api/v1/contracts/{contractId}/review-jobs`.
2. Spring Boot starts a FastAPI review job.
3. React polls `GET /api/v1/contracts/{contractId}/review-jobs/{jobId}`.
4. When FastAPI returns `COMPLETED` with `result`, Spring Boot saves the report to `contract_review_reports`.
5. React receives `savedReviewReport` and displays the saved DB report.
6. On page reload, React calls `GET /api/v1/contracts/{contractId}/review-report` and displays the latest saved report.

Stored fields:

- `jobId`
- `status`
- `overallRiskLevel`
- `summary`
- `reportMarkdown`
- `agentResultsJson`
- `sourcesJson`
- `createdAt`
- `updatedAt`

The same `jobId` is saved only once. Repeated polling for a completed job returns the existing saved report.
If a new report generation fails, the previous saved report remains available.

### 14.1 Get Latest Saved Report

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-report" `
  -Headers @{ "X-Anonymous-Session-Id" = $SessionId }
```

Expected:

```json
{
  "success": true,
  "data": {
    "reviewReportId": 1,
    "contractId": 28,
    "jobId": "review-job-uuid",
    "status": "COMPLETED",
    "overallRiskLevel": "CAUTION",
    "summary": "...",
    "reportMarkdown": "...",
    "agentResults": {},
    "sources": [],
    "createdAt": "...",
    "updatedAt": "..."
  },
  "message": null
}
```

### 14.2 Poll and Save Completed Job

```powershell
do {
  Start-Sleep -Seconds 2
  $SpringJobStatus = Invoke-RestMethod `
    -Method Get `
    -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-jobs/$SpringJobId" `
    -Headers @{ "X-Anonymous-Session-Id" = $SessionId }

  "status=$($SpringJobStatus.data.status), progress=$($SpringJobStatus.data.progress), saved=$($null -ne $SpringJobStatus.data.savedReviewReport)"
} while ($SpringJobStatus.data.status -eq "PENDING" -or $SpringJobStatus.data.status -eq "RUNNING")

$SpringJobStatus.data.savedReviewReport.reviewReportId
```

Expected:

- `savedReviewReport` is present when status is `COMPLETED`.
- Calling the same polling URL again does not insert a duplicate row for the same `jobId`.
- If FastAPI loses an in-memory job after restart, the latest saved report can still be loaded through `/review-report`.

### 14.3 Deleted Contract and Authorization Checks

Deleted contracts should not allow saved report lookup or new job creation.
Different anonymous sessions should receive `403`.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBaseUrl/api/v1/contracts/$ContractId/review-report" `
  -Headers @{ "X-Anonymous-Session-Id" = "other-session-id" }
```

Expected:

- Different anonymous session: `403`
- Missing contract: `404`
- Deleted contract: `404`

## 15. Frontend Persistence Rules

On `AnalysisPage` entry:

- React calls `GET /api/v1/contracts/{contractId}/review-report`.
- If a saved report exists, it is displayed immediately.
- If no saved report exists, the page shows that no comprehensive report has been generated yet.
- If `leaseguard-review-job-{contractId}` exists in `localStorage`, polling resumes.

During regeneration:

- Existing saved report remains visible.
- Download buttons continue to use the saved report.
- The saved report is replaced only after a new job completes and Spring Boot returns `savedReviewReport`.
- If regeneration fails, the existing saved report remains visible.

## 16. Validation Commands

```powershell
cd rag-server
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```
