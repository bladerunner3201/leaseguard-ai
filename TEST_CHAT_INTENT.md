# Chat Intent Routing Test

본 문서는 FastAPI `/rag/chat` 내부 의도 분석 구조를 검증하기 위한 테스트 문서이다. API 응답 구조는 기존과 동일하게 `answer`, `sources`만 반환하며, `topic`, `answerStyle`, `safetyLevel`, `isFollowUp`은 내부 prompt building과 retrieval query rewriting에만 사용한다.

## 구조화된 Intent

| 필드 | 의미 | 예시 |
| --- | --- | --- |
| `topic` | 질문의 계약 이슈 영역 | `deposit_return`, `special_clause_repair`, `registry_check` |
| `answerStyle` | 답변 방식과 톤 | `structured_analysis`, `easy_explanation`, `landlord_question` |
| `safetyLevel` | 법률 판단 민감도 | `normal`, `legal_judgment_sensitive` |
| `isFollowUp` | 후속 질문 여부 | `true`, `false` |

## 의도 분석 단위 테스트

`rag-server` 디렉터리에서 실행한다.

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -c "from app.services.chat_mode_service import detect_chat_intent; questions=['보증금 반환 조건이 위험한지 봐줘','너무 어려운데 쉽게 설명해 줘','비유를 통해 설명해 줘','임대인에게 뭐라고 물어보면 돼?','그 조항을 어떻게 고치면 좋을까?','짧게 핵심만 말해 줘','이 계약 무효야? 소송하면 이겨?']; [print(q, '=>', detect_chat_intent(q)) for q in questions]"
```

기대 결과:

| 질문 | expected topic | expected answerStyle | expected safetyLevel | expected isFollowUp |
| --- | --- | --- | --- | --- |
| 보증금 반환 조건이 위험한지 봐줘 | `deposit_return` | `structured_analysis` | `normal` | `false` |
| 너무 어려운데 쉽게 설명해 줘 | `general_contract_risk` | `easy_explanation` | `normal` | `false` |
| 비유를 통해 설명해 줘 | `general_contract_risk` | `analogy` | `normal` | `false` |
| 임대인에게 뭐라고 물어보면 돼? | `general_contract_risk` | `landlord_question` | `normal` | `false` |
| 그 조항을 어떻게 고치면 좋을까? | `general_contract_risk` | `rewrite_clause` | `normal` | `true` |
| 짧게 핵심만 말해 줘 | `general_contract_risk` | `brief_summary` | `normal` | `false` |
| 이 계약 무효야? 소송하면 이겨? | `general_contract_risk` | `structured_analysis` | `legal_judgment_sensitive` | `false` |

## Retrieval Query Rewriting 확인

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -c "from app.schemas.chat_schema import ChatHistoryMessage; from app.services.chat_mode_service import detect_chat_intent; from app.services.query_rewrite_service import rewrite_retrieval_query; msg='그럼 내가 현실적으로 할 수 있는 일은?'; history=[ChatHistoryMessage(role='user', content='보증금 반환 조건이 위험한지 봐줘'), ChatHistoryMessage(role='assistant', content='보증금 반환 시점과 수리비 부담 특약을 확인해야 합니다.')]; intent=detect_chat_intent(msg); print(intent); print(rewrite_retrieval_query(msg, history, chat_intent=intent))"
```

기대 결과:

- `isFollowUp=True`가 감지된다.
- rewritten query에 최근 대화의 `보증금 반환`, `수리비`, `특약` 맥락이 포함된다.
- rewritten query는 사용자에게 노출되지 않는다.

## `/rag/chat` 직접 호출

FastAPI 서버가 실행 중일 때 사용한다.

```powershell
$body = @{
  anonymousSessionId = "your-session-id"
  contractId = 1
  message = "임대인에게 뭐라고 물어보면 돼?"
  chatHistory = @(
    @{ role = "user"; content = "보증금 반환 조건이 위험한지 봐줘" },
    @{ role = "assistant"; content = "보증금 반환 시점이 명확한지 확인해야 합니다. [Source 1]" }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/rag/chat" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

기대 결과:

- 응답 JSON 구조는 기존처럼 `answer`, `sources`이다.
- 답변은 임대인에게 물어볼 실제 문장 중심으로 나온다.
- 답변 본문에서 근거가 필요한 문장에는 `[Source n]` 형식이 사용된다.
- FastAPI 콘솔 로그에는 `topic`, `answerStyle`, `safetyLevel`, `isFollowUp`, `rewrittenQuery`가 표시된다.
