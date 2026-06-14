# LeaseGuard AI Chat Memory Test

이 문서는 채팅 세션별 구조화 메모리 동작을 검증한다.

## 목표

Spring Boot는 FastAPI에 최근 실제 메시지 8개를 전달하는 구조를 유지한다.  
다만 긴 대화에서 후속 질문 맥락이 사라지는 문제를 줄이기 위해 `chat_sessions.memory_summary`에 구조화된 JSON 메모리를 저장하고, FastAPI 호출 시 `chatHistory` 앞에 보조 assistant 메시지로 함께 전달한다.

기존 `/rag/chat` 응답 구조인 `answer`, `sources`는 변경하지 않는다.

## 저장 형식

`chat_sessions.memory_summary`에는 다음 JSON 문자열을 저장한다.

```json
{
  "topic": "deposit_return_risk_check",
  "issueCategories": [
    "deposit_return",
    "special_clause",
    "repair_cost_restoration"
  ],
  "latestUserConcern": "그럼 내가 현실적으로 할 수 있는 일은?",
  "recommendedNextActions": [
    "보증금 반환 시점과 조건을 계약서 문구로 명확히 확인한다.",
    "특약, 수리비, 원상복구 책임 범위를 임대인에게 문서로 확인한다."
  ]
}
```

## Spring Boot 처리

- 사용자 메시지와 assistant 답변을 저장한다.
- 기존 memory JSON이 있으면 읽어서 issue category를 누적한다.
- 새 사용자 질문과 assistant 답변에서 핵심 이슈를 rule-based로 감지한다.
- `topic`, `issueCategories`, `latestUserConcern`, `recommendedNextActions`를 JSON으로 다시 저장한다.
- FastAPI 호출 시 최근 실제 메시지 8개는 그대로 유지한다.
- memory JSON이 있으면 `chatHistory` 맨 앞에 다음 assistant 메시지를 추가한다.

```text
STRUCTURED_CHAT_MEMORY_JSON
{...memorySummary JSON...}
```

## FastAPI 처리

- `query_rewrite_service.py`가 `STRUCTURED_CHAT_MEMORY_JSON` 마커를 찾아 JSON을 파싱한다.
- `topic`, `issueCategories`, `latestUserConcern`, `recommendedNextActions`를 내부 검색 query에 반영한다.
- category별 확장 키워드를 추가한다.

예:

| issueCategory | query expansion |
|---|---|
| `deposit_return` | 보증금 반환, 반환 지연, 계약 종료, 임차권등기명령 |
| `special_clause` | 특약, 불리한 조항, 임차인 부담, 계약 조건 확인 |
| `repair_cost_restoration` | 수리비, 수선 의무, 원상복구, 노후화 |
| `move_in_fixed_date` | 전입신고, 확정일자, 대항력, 우선변제권 |
| `registry_check` | 등기부등본, 근저당, 압류, 선순위 권리 |
| `jeonse_fraud_prevention` | 전세사기 예방, 보증보험, 시세, 전세가율 |
| `legal_judgment_sensitive` | 법률 판단 단정 불가, 전문가 상담, 무효 여부, 소송 승패 |

## MySQL 확인

```sql
SELECT
  chat_session_id,
  JSON_EXTRACT(memory_summary, '$.topic') AS topic,
  JSON_EXTRACT(memory_summary, '$.issueCategories') AS issue_categories,
  JSON_EXTRACT(memory_summary, '$.latestUserConcern') AS latest_user_concern,
  memory_updated_at
FROM chat_sessions
ORDER BY updated_at DESC;
```

## 검증 시나리오

1. 한 chat session에서 보증금 반환, 특약, 수리비 관련 질문을 여러 번 보낸다.
2. `그럼 내가 현실적으로 할 수 있는 일은?`처럼 짧은 후속 질문을 보낸다.
3. `chat_sessions.memory_summary`가 JSON으로 저장되는지 확인한다.
4. FastAPI 콘솔의 `rewrittenQuery`에 `구조화 메모리 topic`, `issueCategories`, `recommendedNextActions`가 반영되는지 확인한다.
5. 답변이 최근 8개 메시지 바깥으로 밀린 핵심 이슈도 참고하는지 확인한다.

## 현재 한계

- memory JSON 생성은 아직 rule-based 방식이다.
- memory JSON은 API 응답에 노출하지 않는다.
- 다음 단계에서는 `answer_style`, `safety_level`, `top_issue_categories`까지 확장할 수 있다.
