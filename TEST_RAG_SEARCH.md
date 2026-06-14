# LeaseGuard AI RAG Search Quality Test

이 문서는 채팅 검색 품질을 회귀 테스트하기 위한 고정 테스트셋과 실행 방법을 정리한다.  
현재 RAG 검색은 ChromaDB vector search에 metadata/category reranking과 keyword hybrid scoring을 함께 적용한다.

## 1. 전제 조건

- ChromaDB가 `localhost:8001`에서 실행 중이어야 한다.
- FastAPI RAG server가 `localhost:8000`에서 실행 중이어야 한다.
- PowerShell 7 사용을 권장한다. PowerShell 5에서는 한글 입력이 깨질 수 있다.
- OpenAI embedding을 사용하려면 `OPENAI_API_KEY`가 필요하다.

## 2. OpenAI Embedding 설정

기본 설정은 다음과 같다.

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
.\.venv\Scripts\Activate.ps1

$env:OPENAI_API_KEY = "your_api_key_here"
$env:OPENAI_MODEL = "gpt-4o-mini"
$env:EMBEDDING_PROVIDER = "auto"
$env:OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
$env:OPENAI_EMBEDDING_DIMENSIONS = "128"

uvicorn app.main:app --reload --port 8000
```

주의:

- `EMBEDDING_PROVIDER=auto`는 `OPENAI_API_KEY`가 있으면 OpenAI embedding을 사용하고, 없으면 local hash embedding으로 fallback한다.
- 기존 ChromaDB collection이 local hash embedding으로 인덱싱되어 있었다면, OpenAI embedding 활성화 후 reference와 contract를 다시 인덱싱해야 한다.
- 기본 dimension은 기존 MVP collection과의 호환을 위해 `128`로 둔다.

OpenAI embedding을 끄고 fallback 검색만 검증하려면 다음처럼 실행한다.

```powershell
$env:EMBEDDING_PROVIDER = "local"
Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
uvicorn app.main:app --reload --port 8000
```

## 3. Reference 재인덱싱

```powershell
$RagBaseUrl = "http://localhost:8000"

Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/references/index" |
  ConvertTo-Json -Depth 10
```

기대 결과:

- `status`: `INDEXED`
- `collection`: `legal_reference`
- `indexedFiles`: curated reference 포함
- `indexedChunks`: RAG 검색 테스트가 가능한 충분한 chunk 수

## 4. Sample Contract 인덱싱

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/contracts/index" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = "rag-quality-test-session"
    contractId = 9001
    filePath = "D:\leaseguard-ai\leaseguard-ai\data\sample_contracts\sample_lease_contract.txt"
    originalFileName = "sample_lease_contract.txt"
  } | ConvertTo-Json) |
  ConvertTo-Json -Depth 20
```

## 5. 채팅 회귀 테스트셋

| ID | Question | expectedMode | expectedCategories | expectedSourceTypes | expectedKeywords |
|---:|---|---|---|---|---|
| 1 | 보증금 반환 조건이 위험한지 봐줘 | structured_analysis | deposit_return | contract, law, checklist, guide, legal_reference | 보증금, 반환, 지연 |
| 2 | 계약 끝나면 보증금을 바로 돌려받을 수 있어? | structured_analysis | deposit_return | contract, law, legal_reference | 계약 종료, 보증금 반환 |
| 3 | 새 임차인이 구해져야 보증금을 준다는 특약은 괜찮아? | structured_analysis | deposit_return, special_clause_repair | contract, law, checklist | 신규 임차인, 보증금, 특약 |
| 4 | 특약 조항 중 임차인에게 불리한 부분이 있어? | structured_analysis | special_clause_repair | contract, checklist, legal_reference | 특약, 불리, 임차인 |
| 5 | 모든 수리비를 임차인이 부담한다는 조항이 이상한지 확인해줘 | structured_analysis | special_clause_repair | contract, law, standard_contract | 수리비, 임차인 부담, 원상복구 |
| 6 | 원상복구 범위가 너무 넓은지 봐줘 | structured_analysis | special_clause_repair | contract, law, legal_reference, standard_contract | 원상복구, 수리, 책임 범위 |
| 7 | 전입신고와 확정일자는 왜 필요해? | easy_explanation | move_in_fixed_date | law, guide, checklist | 전입신고, 확정일자, 대항력 |
| 8 | 대항력과 우선변제권을 쉽게 설명해줘 | easy_explanation | move_in_fixed_date | law, guide, checklist | 대항력, 우선변제권, 확정일자 |
| 9 | 등기부등본에서 무엇을 확인해야 해? | structured_analysis | registry_check | checklist, guide | 등기부등본, 근저당, 압류 |
| 10 | 근저당이나 압류가 있으면 왜 위험해? | easy_explanation | registry_check, deposit_return | checklist, guide, law | 근저당, 압류, 선순위 |
| 11 | 전세사기 예방을 위해 계약 전에 확인할 것은 뭐야? | structured_analysis | jeonse_fraud_prevention | checklist, guide | 전세사기, 체크리스트, 계약 전 |
| 12 | 보증보험 가입 가능 여부는 어떻게 확인해? | structured_analysis | jeonse_fraud_prevention, deposit_return | checklist, guide | 보증보험, 보증금 |
| 13 | 주변 시세와 보증금을 비교해야 하는 이유가 뭐야? | easy_explanation | jeonse_fraud_prevention | checklist, guide | 시세, 보증금, 전세가율 |
| 14 | 임대인에게 뭐라고 물어보면 돼? | landlord_question | deposit_return, special_clause_repair | contract, legal_reference | 임대인 확인 질문, 보증금, 특약 |
| 15 | 이 조항을 어떻게 고치면 좋을까? | rewrite_clause | special_clause_repair, deposit_return | contract, standard_contract, law | 조항 수정, 특약 문구, 수리비 |
| 16 | 너무 어려운데 비유로 설명해 줘 | analogy | deposit_return, special_clause_repair | contract, legal_reference | 쉬운 설명, 보증금, 특약 |
| 17 | 짧게 핵심만 말해 줘 | brief_summary | deposit_return, special_clause_repair | contract, legal_reference, checklist, standard_contract | 보증금, 특약, 수리비, 원상복구 |
| 18 | 이 계약 무효야? 소송하면 이겨? | legal_judgment_refusal | deposit_return, special_clause_repair | contract, law, legal_reference | 단정 불가, 전문가 상담 |
| 19 | 그럼 내가 현실적으로 할 수 있는 일은? | structured_analysis | deposit_return, special_clause_repair | contract, legal_reference | 후속 질문, 확인사항 |
| 20 | 방금 말한 조항을 임대인에게 어떻게 물어봐야 해? | landlord_question | deposit_return, special_clause_repair | contract, legal_reference | 방금 말한, 임대인, 질문 |
| 21 | 그 조항을 예시 문구로 바꿔줘 | rewrite_clause | special_clause_repair | contract, standard_contract | 예시 문구, 조항 수정 |
| 22 | 제공된 자료만으로 확인하기 어려운 내용은 뭐야? | structured_analysis | standard_contract | contract, legal_reference, checklist, standard_contract | 계약서, 확인, 특약, 보증금 |

## 6. 단일 질문 테스트

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$RagBaseUrl/rag/chat" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    anonymousSessionId = "rag-quality-test-session"
    contractId = 9001
    message = "보증금 반환 조건이 위험한지 봐줘"
    chatHistory = @()
  } | ConvertTo-Json -Depth 10) |
  ConvertTo-Json -Depth 20
```

기대 결과:

- 응답 구조는 기존과 동일하다.
- `answer`와 `sources` 필드가 존재한다.
- sources에는 가능하면 `contract`와 reference source가 함께 포함된다.

```json
{
  "answer": "...",
  "sources": []
}
```

## 7. 전체 질문 실행

```powershell
$Questions = @(
  "보증금 반환 조건이 위험한지 봐줘",
  "계약 끝나면 보증금을 바로 돌려받을 수 있어?",
  "새 임차인이 구해져야 보증금을 준다는 특약은 괜찮아?",
  "특약 조항 중 임차인에게 불리한 부분이 있어?",
  "모든 수리비를 임차인이 부담한다는 조항이 이상한지 확인해줘",
  "원상복구 범위가 너무 넓은지 봐줘",
  "전입신고와 확정일자는 왜 필요해?",
  "대항력과 우선변제권을 쉽게 설명해줘",
  "등기부등본에서 무엇을 확인해야 해?",
  "근저당이나 압류가 있으면 왜 위험해?",
  "전세사기 예방을 위해 계약 전에 확인할 것은 뭐야?",
  "보증보험 가입 가능 여부는 어떻게 확인해?",
  "주변 시세와 보증금을 비교해야 하는 이유가 뭐야?",
  "임대인에게 뭐라고 물어보면 돼?",
  "이 조항을 어떻게 고치면 좋을까?",
  "너무 어려운데 비유로 설명해 줘",
  "짧게 핵심만 말해 줘",
  "이 계약 무효야? 소송하면 이겨?",
  "그럼 내가 현실적으로 할 수 있는 일은?",
  "방금 말한 조항을 임대인에게 어떻게 물어봐야 해?",
  "그 조항을 예시 문구로 바꿔줘",
  "제공된 자료만으로 확인하기 어려운 내용은 뭐야?"
)

$History = @()

foreach ($Question in $Questions) {
  $Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$RagBaseUrl/rag/chat" `
    -ContentType "application/json; charset=utf-8" `
    -Body (@{
      anonymousSessionId = "rag-quality-test-session"
      contractId = 9001
      message = $Question
      chatHistory = $History
    } | ConvertTo-Json -Depth 20)

  ""
  "QUESTION: $Question"
  "SOURCE COUNT: $($Response.sources.Count)"
  $Response.sources |
    Select-Object -First 5 sourceType, sourceTitle, similarityScore |
    Format-Table -AutoSize

  $History += @{ role = "user"; content = $Question }
  $History += @{ role = "assistant"; content = $Response.answer }
  if ($History.Count -gt 10) {
    $History = $History[-10..-1]
  }
}
```

## 8. 평가 기준

- `Hit@3`: 상위 3개 source 중 하나 이상이 expectedCategories, expectedSourceTypes, expectedKeywords 중 하나와 관련 있으면 통과로 본다.
- `Noise count`: 상위 5개 source 중 질문과 명확히 무관한 source 수를 센다. MVP 목표는 `0~2`개이다.
- `contract/reference source mix`: 계약서가 인덱싱되어 있다면 `contract` source가 1개 이상, reference source가 1개 이상 포함되는지 본다.
- `Follow-up continuity`: 후속 질문에서 이전 대화의 보증금 반환, 특약, 수리비 등 핵심 맥락이 sources와 답변에 반영되는지 본다.
- `Mode fit`: `brief_summary`, `landlord_question`, `rewrite_clause`, `legal_judgment_refusal` 등에서 답변 형식이 질문 의도에 맞는지 본다.

수동 평가표:

| ID | Hit@3 | Noise count top5 | Has contract source | Has reference source | Mode fit | Notes |
|---:|---|---:|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |
| 11 |  |  |  |  |  |  |
| 12 |  |  |  |  |  |  |
| 13 |  |  |  |  |  |  |
| 14 |  |  |  |  |  |  |
| 15 |  |  |  |  |  |  |
| 16 |  |  |  |  |  |  |
| 17 |  |  |  |  |  |  |
| 18 |  |  |  |  |  |  |
| 19 |  |  |  |  |  |  |
| 20 |  |  |  |  |  |  |
| 21 |  |  |  |  |  |  |
| 22 |  |  |  |  |  |  |

## 8-1. Latest Regression Result

OpenAI embedding 기준으로 reference와 sample contract를 재인덱싱한 뒤 22개 질문을 실행한 최신 결과이다.

| Metric | Result |
|---|---:|
| Hit@3 | 22/22 |
| Average noise count top5 | 2.45 |
| Contract/reference source mix | 22/22 |

튜닝 내용:

- OpenAI embedding을 `text-embedding-3-small`, `dimensions=128`로 적용했다.
- Vector search 결과에 keyword coverage score와 metadata category bonus를 함께 반영했다.
- 같은 reference title이 과도하게 반복되지 않도록 reference source는 title별 우선 1개만 선택하도록 조정했다.
- `짧게`, `쉽게`, `비유`처럼 style 중심 질문이 들어오면 최근 대화 맥락을 검색 query에 함께 반영하도록 조정했다.

## 9. ChromaDB 컬렉션 확인

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server

.\.venv\Scripts\python.exe -c "from app.vectorstore.chroma_client import get_chroma_client; c=get_chroma_client(); print([col.name for col in c.list_collections()]); print('legal_reference:', c.get_collection('legal_reference').count()); print('user_contracts:', c.get_collection('user_contracts').count())"
```

## 10. OpenAI Embedding 동작 확인

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server

.\.venv\Scripts\python.exe -c "from app.services.embedding_service import get_embedding_provider_name, embed_text; v=embed_text('보증금 반환 조건 확인'); print(get_embedding_provider_name(), len(v), round(sum(x*x for x in v), 4))"
```

기대 결과:

- `OPENAI_API_KEY`가 있고 `EMBEDDING_PROVIDER=auto` 또는 `openai`이면 provider가 `openai`로 표시된다.
- `OPENAI_EMBEDDING_DIMENSIONS=128`이면 vector 길이가 `128`이다.
- API 실패 또는 `EMBEDDING_PROVIDER=local`이면 provider는 `local_hash`로 동작한다.

## 11. 구현 메모

- OpenAI embedding은 `rag-server/app/services/embedding_service.py`에서 처리한다.
- Hybrid retrieval은 `rag-server/app/services/retrieval_service.py`에서 처리한다.
- ChromaDB vector score, metadata category bonus, keyword coverage score를 합산해 reranking한다.
- 기존 `/rag/chat` 응답 구조인 `answer`, `sources`는 변경하지 않는다.
- LangChain은 사용하지 않는다.

## 12. Chat Memory Summary Test

Spring Boot는 FastAPI에 최근 실제 메시지 8개를 전달하는 구조를 유지한다.  
다만 긴 대화에서 후속 질문 맥락이 사라지는 문제를 줄이기 위해 `chat_sessions.memory_summary`에 세션별 핵심 이슈 메모리를 저장하고, FastAPI 호출 시 `chatHistory` 앞에 보조 assistant 메시지로 함께 전달한다.

저장되는 메모리 예:

```text
현재까지의 핵심 이슈:
- 보증금 반환: 관련 조건, 책임 범위, 확인 필요 사항이 대화에서 반복적으로 언급됨.
- 특약/불리한 조항: 관련 조건, 책임 범위, 확인 필요 사항이 대화에서 반복적으로 언급됨.
- 최근 질문: 그럼 내가 현실적으로 할 수 있는 일은?
- 다음 후속 질문에서는 위 이슈를 우선 맥락으로 삼아 답변할 것.
```

MySQL 확인:

```sql
SELECT
  chat_session_id,
  LEFT(memory_summary, 1000) AS memory_summary_preview,
  memory_updated_at
FROM chat_sessions
ORDER BY updated_at DESC;
```

검증 시나리오:

1. 한 chat session에서 보증금 반환, 특약, 수리비 관련 질문을 여러 번 보낸다.
2. 이후 `그럼 내가 현실적으로 할 수 있는 일은?`처럼 짧은 후속 질문을 보낸다.
3. `chat_sessions.memory_summary`가 갱신되는지 확인한다.
4. 답변이 최근 8개 메시지 바깥으로 밀린 핵심 이슈도 참고하는지 확인한다.

현재 한계:

- 1차 구현은 OpenAI 요약이 아니라 rule-based keyword 요약이다.
- API 응답 구조에는 memory summary를 노출하지 않는다.
- 향후 `topic`, `answer_style`, `safety_level`, `top_issue_categories`를 구조화해 저장하면 더 안정적으로 개선할 수 있다.
