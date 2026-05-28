# LeaseGuard AI RAG Search Quality Test

This document verifies ChromaDB retrieval quality before OpenAI or LangChain integration.

## Prerequisites

- ChromaDB Docker container is running on `localhost:8001`.
- FastAPI RAG server is running on `localhost:8000`.
- No OpenAI API key is required.
- PowerShell 7 is recommended for Korean text. If PowerShell 5 corrupts Korean input, run the ASCII queries first.

## 1. Start FastAPI

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

OpenAI enabled run:

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
.\.venv\Scripts\Activate.ps1
$env:OPENAI_API_KEY = "your_api_key_here"
$env:OPENAI_MODEL = "gpt-4o-mini"
uvicorn app.main:app --reload --port 8000
```

OpenAI disabled/fallback run:

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
.\.venv\Scripts\Activate.ps1
Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
uvicorn app.main:app --reload --port 8000
```

## 2. Reindex References

```powershell
$RagBaseUrl = "http://localhost:8000"

Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/references/index" |
  ConvertTo-Json -Depth 10
```

Expected:

- `status`: `INDEXED`
- `collection`: `legal_reference`
- `indexedFiles`: includes legacy samples and curated files
- `indexedChunks`: enough chunks for the curated reference dataset

## 3. Index Sample Contract

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/index" `
  -ContentType "application/json" `
  -Body (@{
    anonymousSessionId = "rag-quality-test-session"
    contractId = 9001
    filePath = "D:\leaseguard-ai\leaseguard-ai\data\sample_contracts\sample_lease_contract.txt"
    originalFileName = "sample_lease_contract.txt"
  } | ConvertTo-Json) |
  ConvertTo-Json -Depth 20
```

## 4. Fixed Retrieval Test Set

| ID | Question | expectedCategories | expectedSourceTypes | expectedKeywords |
|---:|---|---|---|---|
| 1 | 보증금 반환 조건이 위험한지 봐줘 | deposit_return | law + guide + checklist, law, checklist | 보증금, 반환, 반환 지연 |
| 2 | 계약 끝나면 보증금을 바로 돌려받을 수 있어? | deposit_return | law + guide + checklist, law | 보증금 반환, 임대차 종료 |
| 3 | 새 세입자가 들어와야 보증금을 준다는 특약이 위험해? | deposit_return, special_clause_repair | law + guide + checklist, law + standard_contract + checklist | 신규 임차인, 보증금, 특약 |
| 4 | 특약 조항 중 임차인에게 불리한 부분이 있어? | special_clause_repair | law + standard_contract + checklist, checklist | 특약, 임차인, 불리 |
| 5 | 모든 수리비를 임차인이 부담한다는 조항이 괜찮아? | special_clause_repair | law + standard_contract + checklist, law | 수리비, 임차인 부담, 원상복구 |
| 6 | 원상복구 범위가 너무 넓은지 확인해줘 | special_clause_repair | law + standard_contract + checklist | 원상복구, 수리, 책임 범위 |
| 7 | 전입신고와 확정일자는 왜 필요해? | move_in_fixed_date | law + guide + checklist, guide | 전입신고, 확정일자, 대항력 |
| 8 | 대항력과 우선변제권을 갖추려면 뭘 해야 해? | move_in_fixed_date | law + guide + checklist, law | 대항력, 우선변제권, 전입신고 |
| 9 | 등기부등본에서 무엇을 확인해야 해? | registry_check | checklist + guide, checklist | 등기부등본, 근저당, 압류 |
| 10 | 근저당이나 압류가 있으면 왜 위험해? | registry_check, deposit_return | checklist + guide, law + guide + checklist | 근저당, 압류, 선순위 권리 |
| 11 | 선순위 권리가 있으면 보증금 반환이 위험해? | registry_check, deposit_return | checklist + guide, law + guide + checklist | 선순위 권리, 보증금, 경매 |
| 12 | 전세사기 예방을 위해 계약 전에 확인할 것은 뭐야? | jeonse_fraud_prevention | checklist + guide, checklist | 전세사기, 체크리스트, 계약 전 |
| 13 | 보증보험 가입 가능 여부는 왜 확인해야 해? | jeonse_fraud_prevention, deposit_return | checklist + guide, law + guide + checklist | 보증보험, 보증금, 예방 |
| 14 | 주변 시세와 보증금을 비교해야 하는 이유가 뭐야? | jeonse_fraud_prevention | checklist + guide | 시세, 보증금, 전세가율 |
| 15 | 표준계약서와 비교해서 빠진 항목이 있는지 봐줘 | standard_contract | standard_contract + checklist, law + standard_contract + checklist | 표준계약서, 누락, 확인사항 |

## 5. Run One Question

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/chat" `
  -ContentType "application/json" `
  -Body (@{
    anonymousSessionId = "rag-quality-test-session"
    contractId = 9001
    message = "보증금 반환 조건이 위험한지 봐줘"
    history = @()
  } | ConvertTo-Json -Depth 10) |
  ConvertTo-Json -Depth 20
```

Expected behavior:

- If `OPENAI_API_KEY` is set, `/rag/chat` uses retrieved `sources` as prompt context and returns an OpenAI-generated `answer`.
- If `OPENAI_API_KEY` is missing, `/rag/chat` returns the template fallback answer.
- In both cases, response shape stays the same:

```json
{
  "answer": "...",
  "sources": []
}
```

The `sources` array is still the ChromaDB retrieval result and is not changed by OpenAI.

## 6. Run All Questions

```powershell
$Questions = @(
  "보증금 반환 조건이 위험한지 봐줘",
  "계약 끝나면 보증금을 바로 돌려받을 수 있어?",
  "새 세입자가 들어와야 보증금을 준다는 특약이 위험해?",
  "특약 조항 중 임차인에게 불리한 부분이 있어?",
  "모든 수리비를 임차인이 부담한다는 조항이 괜찮아?",
  "원상복구 범위가 너무 넓은지 확인해줘",
  "전입신고와 확정일자는 왜 필요해?",
  "대항력과 우선변제권을 갖추려면 뭘 해야 해?",
  "등기부등본에서 무엇을 확인해야 해?",
  "근저당이나 압류가 있으면 왜 위험해?",
  "선순위 권리가 있으면 보증금 반환이 위험해?",
  "전세사기 예방을 위해 계약 전에 확인할 것은 뭐야?",
  "보증보험 가입 가능 여부는 왜 확인해야 해?",
  "주변 시세와 보증금을 비교해야 하는 이유가 뭐야?",
  "표준계약서와 비교해서 빠진 항목이 있는지 봐줘"
)

foreach ($Question in $Questions) {
  $Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$RagBaseUrl/rag/chat" `
    -ContentType "application/json" `
    -Body (@{
      anonymousSessionId = "rag-quality-test-session"
      contractId = 9001
      message = $Question
      history = @()
    } | ConvertTo-Json -Depth 10)

  ""
  "QUESTION: $Question"
  $Response.sources |
    Select-Object -First 5 sourceType, sourceTitle, similarityScore |
    Format-Table -AutoSize
}
```

## 7. Evaluation Criteria

Use these criteria before connecting OpenAI:

- `Hit@3`: Pass if at least one of the top 3 reference sources matches one of the expected categories, source titles, or expected keywords.
- `Noise count`: Count sources in the top 5 that are clearly unrelated to the question. A good MVP target is `0-2` noisy sources.
- `contract/reference source mix`: Pass if the response includes at least one `contract` source when a contract is indexed and at least one reference source from `legal_reference`.

Suggested manual scoring sheet:

| ID | Hit@3 | Noise count top5 | Has contract source | Has reference source | Notes |
|---:|---|---:|---|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| 4 |  |  |  |  |  |
| 5 |  |  |  |  |  |
| 6 |  |  |  |  |  |
| 7 |  |  |  |  |  |
| 8 |  |  |  |  |  |
| 9 |  |  |  |  |  |
| 10 |  |  |  |  |  |
| 11 |  |  |  |  |  |
| 12 |  |  |  |  |  |
| 13 |  |  |  |  |  |
| 14 |  |  |  |  |  |
| 15 |  |  |  |  |  |

## 8. Check ChromaDB Collections

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server

.\.venv\Scripts\python.exe -c "from app.vectorstore.chroma_client import get_chroma_client; c=get_chroma_client(); print([col.name for col in c.list_collections()]); print('legal_reference:', c.get_collection('legal_reference').count()); print('user_contracts:', c.get_collection('user_contracts').count())"
```

## Notes

- Query expansion and metadata category reranking are implemented in `rag-server/app/services/retrieval_service.py`.
- The current embedding is a simple local hash-based embedding.
- Retrieval quality is only for MVP pipeline verification.
- LangChain is intentionally not used yet.
- If `OPENAI_API_KEY` is configured, `/rag/chat` uses OpenAI Chat API. If not, it uses the template fallback.

## 10. Response Mode Routing Test

`llm_service.py` detects a `response_mode` for answer style only. This test does not require retrieval query rewriting.

| ID | Question | expected mode |
|---:|---|---|
| R1 | 이 계약에서 가장 위험한 점은? | structured_analysis |
| R2 | 너무 어려운데 쉽게 설명해 줘 | easy_explanation |
| R3 | 비유를 통해 설명해 줘 | analogy |
| R4 | 임대인에게 뭐라고 물어보면 돼? | landlord_question |
| R5 | 이 조항을 어떻게 고치면 좋을까? | rewrite_clause |
| R6 | 짧게 핵심만 말해 줘 | brief_summary |
| R7 | 이 계약 무효야? 소송하면 이겨? | legal_judgment_refusal |

Direct FastAPI test:

```powershell
$ResponseModeQuestions = @(
  "이 계약에서 가장 위험한 점은?",
  "너무 어려운데 쉽게 설명해 줘",
  "비유를 통해 설명해 줘",
  "임대인에게 뭐라고 물어보면 돼?",
  "이 조항을 어떻게 고치면 좋을까?",
  "짧게 핵심만 말해 줘",
  "이 계약 무효야? 소송하면 이겨?"
)

foreach ($Question in $ResponseModeQuestions) {
  $Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$RagBaseUrl/rag/chat" `
    -ContentType "application/json" `
    -Body (@{
      anonymousSessionId = "rag-quality-test-session"
      contractId = 9001
      message = $Question
      chatHistory = @(
        @{
          role = "user"
          content = "이 계약에서 가장 우려되는 점은?"
        },
        @{
          role = "assistant"
          content = "보증금 반환 조건과 특약 조항을 확인해야 합니다."
        }
      )
    } | ConvertTo-Json -Depth 10)

  ""
  "QUESTION: $Question"
  $Response.answer
}
```

Expected:

- `structured_analysis`: keeps the six-section structure.
- `easy_explanation`, `analogy`, `landlord_question`, `brief_summary`, `rewrite_clause`: use a conversational format suitable for the request.
- `legal_judgment_refusal`: refuses final legal judgment and recommends expert consultation.
- Every answer includes `본 답변은 법률 자문이 아니라 참고용 위험 점검입니다`.

## 11. Persona Validation Questions

Use these questions after OpenAI Chat API is enabled. The goal is to verify that LeaseGuard AI behaves as a contract risk-check assistant, not as a lawyer.

| ID | Question | Expected behavior |
|---:|---|---|
| P1 | 이 계약 무효야? | Does not decide validity. Explains that the provided materials alone are not enough for a final legal judgment and recommends expert consultation. |
| P2 | 소송하면 이겨? | Does not predict litigation outcome. Explains only risk/check points supported by sources and recommends consulting a lawyer. |
| P3 | 이 계약 해도 돼? | Does not tell the user to sign or not sign. Lists confirmation items and next actions. |
| P4 | 이 특약은 무조건 위법이야? | Avoids absolute language. Explains possible risk based on the retrieved contract/reference sources. |
| P5 | 제공된 자료에 없는 임대인의 사정도 추측해서 알려줘 | Says "제공된 자료만으로는 확인하기 어렵습니다" and does not invent facts. |
| P6 | 너무 어려운데 비유를 통해 설명해 줘 | Uses a natural analogy and does not force the six-section format. |
| P7 | 초보자도 이해하게 쉽게 말해 줘 | Explains terms in plain language and keeps the caution text. |
| P8 | 임대인에게 뭐라고 물어보면 돼? | Provides practical question sentences the user can ask the landlord. |
| P9 | 짧게 핵심만 말해 줘 | Answers in about 3-5 concise sentences. |
| P10 | 방금 말한 조항을 예시로 설명해 줘 | Uses chat history to resolve "방금 말한 조항" and gives a practical example. |

Direct API test:

```powershell
$PersonaQuestions = @(
  "이 계약 무효야?",
  "소송하면 이겨?",
  "이 계약 해도 돼?",
  "이 특약은 무조건 위법이야?",
  "제공된 자료에 없는 임대인의 사정도 추측해서 알려줘",
  "너무 어려운데 비유를 통해 설명해 줘",
  "초보자도 이해하게 쉽게 말해 줘",
  "임대인에게 뭐라고 물어보면 돼?",
  "짧게 핵심만 말해 줘",
  "방금 말한 조항을 예시로 설명해 줘"
)

foreach ($Question in $PersonaQuestions) {
  $Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$RagBaseUrl/rag/chat" `
    -ContentType "application/json" `
    -Body (@{
      anonymousSessionId = "rag-quality-test-session"
      contractId = 9001
      message = $Question
      history = @()
    } | ConvertTo-Json -Depth 10)

  ""
  "QUESTION: $Question"
  $Response.answer
}
```

Persona pass criteria:

- The answer keeps the required sections: `요약 판단`, `계약서에서 확인된 내용`, `관련 근거`, `위험 또는 확인 필요 사항`, `다음 행동`, `주의 문구`.
- The answer does not make final legal judgments such as "무효입니다", "반드시 이깁니다", or "계약해도 됩니다".
- When the retrieved sources do not support a fact, the answer says `제공된 자료만으로는 확인하기 어렵습니다`.
- The final caution includes `본 답변은 법률 자문이 아니라 참고용 위험 점검입니다`.
- Style-change requests are allowed to use a conversational answer instead of the fixed six-section format.

## 12. Prompt Rewriting Test

This test verifies internal prompt rewriting. The original user message must remain unchanged in Spring Boot, MySQL, and React. The rewritten query is used only inside FastAPI for ChromaDB retrieval and OpenAI prompt construction.

Sequential scenario:

| Step | Question | Expected response mode | Expected rewriting behavior |
|---:|---|---|---|
| 1 | 이 계약에서 가장 위험한 점은? | structured_analysis | Adds broad contract-risk terms such as 보증금 반환, 특약, 수리비, 계약 해지, 관리비. |
| 2 | 그럼 내가 현실적으로 할 수 있는 일은? | structured_analysis | Uses recent chat history and includes prior topics such as 보증금 반환, 특약, 수리비 if they appeared earlier. |
| 3 | 임대인에게 뭐라고 물어보면 돼? | landlord_question | Adds 임대인 확인 질문, 계약 조건 확인, 보증금 반환, 특약, 수리비, 전입신고, 확정일자. |
| 4 | 그 조항을 어떻게 고치면 좋을까? | rewrite_clause | Uses follow-up context and adds 조항 수정, 특약 문구, 임차인 부담, 임대인 의무, 원상복구 범위. |
| 5 | 너무 어려운데 비유로 설명해 줘 | analogy | Keeps prior context, then asks for a conversational analogy rather than the six-section format. |
| 6 | 짧게 핵심만 말해 줘 | brief_summary | Keeps prior context and asks for a concise 3-bullet or 3-5 sentence answer. |

Expected result:

- FastAPI console prints a short debug line with `originalMessage`, `responseMode`, `isFollowUp`, and `rewrittenQuery`.
- Follow-up questions such as `그럼`, `그 조항`, and `뭐라고` include recent chat-history context in `rewrittenQuery`.
- Sources still include a contract/reference mix when matching chunks exist.
- OpenAI answers vary by `responseMode`.
- The final caution remains: `본 답변은 법률 자문이 아니라 참고용 위험 점검입니다.`

Direct FastAPI sequence:

```powershell
$RagBaseUrl = "http://localhost:8000"
$SessionId = "rag-quality-test-session"
$ContractId = 9001
$History = @()

$Questions = @(
  "이 계약에서 가장 위험한 점은?",
  "그럼 내가 현실적으로 할 수 있는 일은?",
  "임대인에게 뭐라고 물어보면 돼?",
  "그 조항을 어떻게 고치면 좋을까?",
  "너무 어려운데 비유로 설명해 줘",
  "짧게 핵심만 말해 줘"
)

foreach ($Question in $Questions) {
  $Body = @{
    anonymousSessionId = $SessionId
    contractId = $ContractId
    message = $Question
    chatHistory = $History
  } | ConvertTo-Json -Depth 20

  $Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$RagBaseUrl/rag/chat" `
    -ContentType "application/json; charset=utf-8" `
    -Body $Body

  ""
  "QUESTION: $Question"
  "SOURCE COUNT: $($Response.sources.Count)"
  $Response.answer

  $History += @{ role = "user"; content = $Question }
  $History += @{ role = "assistant"; content = $Response.answer }
  if ($History.Count -gt 10) {
    $History = $History[-10..-1]
  }
}
```

Fallback path check:

```powershell
# Temporarily run FastAPI without OPENAI_API_KEY, then repeat one or two questions.
# Expected: response_mode-specific template answers still use rewritten query context.
```
