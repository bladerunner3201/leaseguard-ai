# LeaseGuard AI MVP API Test Commands

현재 Spring Boot Controller 구현 기준 PowerShell 테스트 명령어입니다.

전제:

- Backend: `http://localhost:8080`
- FastAPI RAG server: `http://localhost:8000`
- MySQL container: `leaseguard-mysql`
- PowerShell 7 이상 권장
- 계약서 업로드는 `@RequestParam("file") MultipartFile file`이므로 `multipart/form-data`로 호출합니다.

## 0. 공통 변수

```powershell
$BaseUrl = "http://localhost:8080"
$ContractFile = "D:\leaseguard-ai\leaseguard-ai\data\sample_contracts\sample_lease_contract.txt"
```

## 1. Anonymous Session 생성

```powershell
$sessionResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/api/v1/anonymous-sessions"

$sessionResponse | ConvertTo-Json -Depth 10
```

## 2. anonymousSessionId 변수 저장

```powershell
$anonymousSessionId = $sessionResponse.data.anonymousSessionId
$Headers = @{
  "X-Anonymous-Session-Id" = $anonymousSessionId
}

$anonymousSessionId
```

## 3. 계약서 업로드

현재 구현:

- `POST /api/v1/contracts`
- Header: `X-Anonymous-Session-Id`
- Form field: `file`
- Controller parameter: `@RequestParam("file") MultipartFile file`

```powershell
$uploadResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/api/v1/contracts" `
  -Headers $Headers `
  -Form @{
    file = Get-Item $ContractFile
  }

$uploadResponse | ConvertTo-Json -Depth 20
```

응답에서 `contractId`를 저장합니다.

```powershell
$contractId = $uploadResponse.data.contract.contractId
$contractId
```

이 API는 내부에서 FastAPI `POST /rag/contracts/index`를 호출합니다.

## 4. 계약서 목록 조회

```powershell
$contractsResponse = Invoke-RestMethod `
  -Method Get `
  -Uri "$BaseUrl/api/v1/contracts" `
  -Headers $Headers

$contractsResponse | ConvertTo-Json -Depth 20
```

## 5. 계약서 상세 조회

```powershell
$contractDetailResponse = Invoke-RestMethod `
  -Method Get `
  -Uri "$BaseUrl/api/v1/contracts/$contractId" `
  -Headers $Headers

$contractDetailResponse | ConvertTo-Json -Depth 20
```

## 6. 계약서 분석 결과 조회

```powershell
$analysisResponse = Invoke-RestMethod `
  -Method Get `
  -Uri "$BaseUrl/api/v1/contracts/$contractId/analysis" `
  -Headers $Headers

$analysisResponse | ConvertTo-Json -Depth 20
```

## 7. 채팅 세션 생성

현재 구현:

- `POST /api/v1/chat-sessions`
- JSON body: `contractId`, `title`

```powershell
$chatSessionResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/api/v1/chat-sessions" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    contractId = $contractId
    title = "sample contract chat"
  } | ConvertTo-Json)

$chatSessionResponse | ConvertTo-Json -Depth 20
```

응답에서 `chatSessionId`를 저장합니다.

```powershell
$chatSessionId = $chatSessionResponse.data.chatSessionId
$chatSessionId
```

## 8. 채팅 메시지 전송

현재 구현:

- `POST /api/v1/chat-sessions/{chatSessionId}/messages`
- JSON body: `contractId`, `message`

```powershell
$chatAnswerResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/api/v1/chat-sessions/$chatSessionId/messages" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    contractId = $contractId
    message = "이 계약서에서 보증금 반환 조건이 위험한지 봐줘"
  } | ConvertTo-Json)

$chatAnswerResponse | ConvertTo-Json -Depth 20
```

이 API는 내부에서 FastAPI `POST /rag/chat`을 호출합니다.

## 9. 채팅 메시지 목록 조회

```powershell
$messagesResponse = Invoke-RestMethod `
  -Method Get `
  -Uri "$BaseUrl/api/v1/chat-sessions/$chatSessionId/messages" `
  -Headers $Headers

$messagesResponse | ConvertTo-Json -Depth 20
```

## 10. 다른 Anonymous Session 접근 403 확인

새 anonymous session을 하나 더 생성합니다.

```powershell
$otherSessionResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/api/v1/anonymous-sessions"

$otherAnonymousSessionId = $otherSessionResponse.data.anonymousSessionId
$OtherHeaders = @{
  "X-Anonymous-Session-Id" = $otherAnonymousSessionId
}
```

다른 세션으로 기존 계약서에 접근합니다. 정상이라면 HTTP `403 Forbidden`입니다.

```powershell
try {
  Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/api/v1/contracts/$contractId" `
    -Headers $OtherHeaders
} catch {
  $statusCode = [int]$_.Exception.Response.StatusCode
  $body = $_.ErrorDetails.Message

  "StatusCode: $statusCode"
  $body
}
```

다른 세션으로 기존 채팅 메시지 목록에 접근합니다. 정상이라면 HTTP `403 Forbidden`입니다.

```powershell
try {
  Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/api/v1/chat-sessions/$chatSessionId/messages" `
    -Headers $OtherHeaders
} catch {
  $statusCode = [int]$_.Exception.Response.StatusCode
  $body = $_.ErrorDetails.Message

  "StatusCode: $statusCode"
  $body
}
```

## 11. MySQL 테이블 데이터 확인 SQL

Docker 컨테이너 안의 MySQL client에 접속합니다.

```powershell
docker exec -it leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard
```

접속 후 실행합니다.

```sql
SHOW TABLES;

SELECT *
FROM anonymous_sessions
ORDER BY created_at DESC;

SELECT contract_id, anonymous_session_id, original_file_name, stored_file_path, status, created_at
FROM contracts
ORDER BY contract_id DESC;

SELECT analysis_id, contract_id, overall_risk_level, summary, risk_items_json, created_at
FROM contract_analysis_results
ORDER BY analysis_id DESC;

SELECT chat_session_id, anonymous_session_id, contract_id, title, created_at, updated_at
FROM chat_sessions
ORDER BY chat_session_id DESC;

SELECT message_id, chat_session_id, role, content, created_at
FROM chat_messages
ORDER BY message_id DESC;

SELECT source_id, message_id, source_type, source_title, page_number, similarity_score
FROM message_sources
ORDER BY source_id DESC;
```

한 줄 명령으로 빠르게 확인하려면 다음을 사용합니다.

```powershell
docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SHOW TABLES;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT anonymous_session_id, created_at, last_accessed_at FROM anonymous_sessions ORDER BY created_at DESC LIMIT 5;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT contract_id, anonymous_session_id, original_file_name, status, created_at FROM contracts ORDER BY contract_id DESC LIMIT 5;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT analysis_id, contract_id, overall_risk_level, summary, created_at FROM contract_analysis_results ORDER BY analysis_id DESC LIMIT 5;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT chat_session_id, anonymous_session_id, contract_id, title, updated_at FROM chat_sessions ORDER BY chat_session_id DESC LIMIT 5;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT message_id, chat_session_id, role, LEFT(content, 120) AS content_preview, created_at FROM chat_messages ORDER BY message_id DESC LIMIT 10;"

docker exec leaseguard-mysql mysql -u leaseguard -pleaseguard123 leaseguard -e "SELECT source_id, message_id, source_type, source_title, page_number, similarity_score FROM message_sources ORDER BY source_id DESC LIMIT 10;"
```

## 12. FastAPI RAG 서버가 꺼져 있을 때

현재 backend 구현에서 FastAPI를 내부 호출하는 API는 다음입니다.

- `POST /api/v1/contracts`
  - 내부 호출: `POST /rag/contracts/index`
- `POST /api/v1/chat-sessions/{chatSessionId}/messages`
  - 내부 호출: `POST /rag/chat`

FastAPI 서버가 꺼져 있으면 Spring `RestClient` 호출이 실패하고, 현재 `GlobalExceptionHandler`의 일반 예외 처리에 의해 HTTP `500 Internal Server Error` 응답이 반환됩니다.

계약서 업로드 실패 응답 예시는 다음과 같습니다.

```json
{
  "success": false,
  "data": null,
  "message": "I/O error on POST request for \"http://localhost:8000/rag/contracts/index\": Connection refused: getsockopt"
}
```

채팅 메시지 전송 실패 응답 예시는 다음과 같습니다.

```json
{
  "success": false,
  "data": null,
  "message": "I/O error on POST request for \"http://localhost:8000/rag/chat\": Connection refused: getsockopt"
}
```

두 API 모두 트랜잭션 안에서 예외가 발생하므로 계약서/분석 결과 저장 또는 채팅 메시지 저장은 롤백됩니다.
