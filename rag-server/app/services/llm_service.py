import os
import re

from openai import OpenAI

from app.schemas.chat_schema import ChatHistoryMessage, RagSource

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
CAUTION_TEXT = "본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."

STRUCTURED_ANALYSIS = "structured_analysis"
EASY_EXPLANATION = "easy_explanation"
ANALOGY = "analogy"
LANDLORD_QUESTION = "landlord_question"
BRIEF_SUMMARY = "brief_summary"
REWRITE_CLAUSE = "rewrite_clause"
LEGAL_JUDGMENT_REFUSAL = "legal_judgment_refusal"

# Final-judgment requests only. Avoid broad terms like "전세사기" so checklist questions do not get misrouted.
LEGAL_JUDGMENT_MARKERS = [
    "무효",
    "위법",
    "소송",
    "이겨",
    "계약해도 돼",
    "계약 해도 돼",
    "계약해도 되",
    "계약 해도 되",
    "사기야",
    "사기 맞아",
    "고소",
    "고발",
]
REWRITE_CLAUSE_MARKERS = [
    "고쳐",
    "수정",
    "바꿔",
    "문구 수정",
    "문구 바꿔",
    "문구 만들어",
    "문구 작성",
    "특약 써",
    "조항 작성",
    "어떻게 고치",
]
LANDLORD_QUESTION_MARKERS = ["임대인에게", "뭐라고 물어", "어떻게 말", "어떻게 요구", "어떻게 물어"]
ANALOGY_MARKERS = ["비유", "예시", "예를 들어", "일상적으로 설명"]
EASY_EXPLANATION_MARKERS = ["쉽게", "너무 어려", "초보", "다시 설명", "풀어서 설명"]
BRIEF_SUMMARY_MARKERS = ["짧게", "핵심만", "요약", "세 줄"]
FOLLOW_UP_MARKERS = [
    "그럼",
    "그 부분",
    "방금",
    "방금 말한",
    "그 조항",
    "이 부분",
    "그건",
    "그거",
]

RESPONSE_MODE_QUERY_KEYWORDS = {
    STRUCTURED_ANALYSIS: ["위험 분석", "계약서 확인사항", "보증금 반환", "특약", "수리비", "계약 해지", "관리비"],
    EASY_EXPLANATION: ["쉬운 설명", "핵심 위험", "확인사항", "법률 용어 풀이"],
    ANALOGY: ["핵심 위험", "쉬운 설명", "계약 조건", "보증금 반환", "특약", "수리비"],
    LANDLORD_QUESTION: ["임대인 확인 질문", "계약 조건 확인", "보증금 반환", "특약", "수리비", "전입신고", "확정일자"],
    BRIEF_SUMMARY: ["핵심 요약", "주요 위험", "확인사항"],
    REWRITE_CLAUSE: ["조항 수정", "특약 문구", "임차인 부담", "임대인 의무", "보증금 반환 조건", "수리비 부담 범위", "원상복구 범위"],
    LEGAL_JUDGMENT_REFUSAL: ["위험 요소", "단정 불가", "전문가 상담", "무효 여부", "위법 여부", "소송 승패", "계약 확인사항"],
}

CONTEXT_KEYWORDS = [
    "보증금",
    "반환",
    "돌려받",
    "특약",
    "수리비",
    "수선",
    "원상복구",
    "전입신고",
    "확정일자",
    "대항력",
    "우선변제권",
    "등기부",
    "근저당",
    "압류",
    "선순위",
    "보증보험",
    "전세사기",
    "시세",
    "관리비",
    "계약 해지",
    "해지",
]

SYSTEM_PROMPT = f"""
당신은 LeaseGuard AI입니다.
LeaseGuard AI는 부동산 임대차계약서를 처음 읽는 사용자를 위한 계약 위험 점검 보조 챗봇입니다.
사용자는 법률 비전문가라고 가정하고, 친절하고 쉬운 한국어 대화체로 답변하세요.

공통 안전 규칙:
- 제공된 계약서 조각과 reference source에 근거해서만 답변하세요.
- sources에 없는 내용은 단정하지 말고 "제공된 자료만으로는 확인하기 어렵습니다"라고 말하세요.
- 계약 무효 여부, 위법 여부, 소송 승패, 계약 체결 가능 여부를 단정하지 마세요.
- 법률 판단을 요구받으면 확인 가능한 위험 요소만 설명하고 전문가 상담을 권장하세요.
- chatHistory가 있으면 "그 부분", "방금 말한 내용", "그 조항" 같은 표현을 이전 대화 맥락으로 해석하세요.
- 모든 모드에서 마지막에는 자연스럽게 "{CAUTION_TEXT}"를 포함하세요.
- response_mode는 답변의 목표와 톤을 정하는 힌트이며, 고정 출력 템플릿이 아닙니다.
- structured_analysis 외의 모드에서는 정해진 제목이나 섹션을 반복하지 마세요.
- 사용자의 질문에 필요한 만큼만 답하고, 매번 같은 문장 구조를 반복하지 마세요.
- 후속 질문은 이전 대화 흐름을 따라 자연스럽게 이어서 답하세요.
- 어떤 모드에서도 sources 근거 제한과 법률 자문이 아니라는 원칙은 유지하세요.

response_mode별 답변 전략:

1. structured_analysis
기본 계약서 위험 분석 모드입니다. 기본적으로 아래 6개 섹션을 사용하되, 질문 범위가 좁으면 각 섹션을 짧게 처리하세요.
불필요하게 긴 설명을 반복하지 마세요.
1. 요약 판단
2. 계약서에서 확인된 내용
3. 관련 근거
4. 위험 또는 확인 필요 사항
5. 다음 행동
6. 주의 문구

2. easy_explanation
제목을 강제하지 말고 자연스러운 문단으로 답하세요.
어려운 용어를 쉬운 말로 바꾸고, 사용자가 이미 이해한 내용은 반복하지 마세요.

3. analogy
비유를 먼저 제시하되 반드시 긴 구조를 만들 필요는 없습니다.
비유 → 실제 계약 상황 연결 → 확인할 점 정도만 자연스럽게 설명하세요.
비유를 과장하지 말고 sources에 있는 내용과 연결하세요.

4. landlord_question
사용자가 바로 쓸 수 있는 문장을 2~4개 제시하세요.
"부드러운 표현/명확한 표현" 구분은 필요할 때만 사용하세요.
문자 메시지처럼 자연스럽게 쓸 수 있는 문장도 허용하세요.

5. brief_summary
최대 bullet 3개 또는 5문장 이내로 답하세요.
출처 설명을 길게 늘리지 말고, 핵심 위험과 다음 행동만 남기세요.

6. rewrite_clause
조항 수정 방향과 예시 문구를 제시하세요.
예시 문구는 참고용이라고 밝히고, 지나치게 법률 문안처럼 확정하지 마세요.
실제 계약서 반영 전 전문가 검토가 필요하다는 점을 안내하세요.

7. legal_judgment_refusal
계약 무효 여부, 위법 여부, 소송 승패, 계약 체결 가능 여부를 단정하지 마세요.
"제공된 자료만으로는 단정하기 어렵습니다"라는 취지를 포함하세요.
단순히 거절만 하지 말고 "대신 지금 확인할 수 있는 것은..."처럼 이어서 sources에서 확인 가능한 위험 요소와 다음 행동을 안내하세요.
""".strip()


def detect_response_mode(message: str) -> str:
    normalized = (message or "").lower()

    if any(marker in normalized for marker in LEGAL_JUDGMENT_MARKERS):
        return LEGAL_JUDGMENT_REFUSAL
    if any(marker in normalized for marker in REWRITE_CLAUSE_MARKERS):
        return REWRITE_CLAUSE
    if any(marker in normalized for marker in LANDLORD_QUESTION_MARKERS):
        return LANDLORD_QUESTION
    if any(marker in normalized for marker in ANALOGY_MARKERS):
        return ANALOGY
    if any(marker in normalized for marker in EASY_EXPLANATION_MARKERS):
        return EASY_EXPLANATION
    if any(marker in normalized for marker in BRIEF_SUMMARY_MARKERS):
        return BRIEF_SUMMARY

    return STRUCTURED_ANALYSIS


def detect_follow_up(message: str) -> bool:
    normalized = message or ""
    return any(marker in normalized for marker in FOLLOW_UP_MARKERS)


def rewrite_retrieval_query(
    message: str,
    chat_history: list[ChatHistoryMessage] | None,
    response_mode: str,
    is_follow_up: bool,
) -> str:
    """Build an internal-only query for vector retrieval while preserving the user's original message."""
    parts: list[str] = [(message or "").strip()]

    if is_follow_up:
        context = _extract_rewrite_context(chat_history or [])
        if context:
            parts.append(context)

    parts.extend(RESPONSE_MODE_QUERY_KEYWORDS.get(response_mode, RESPONSE_MODE_QUERY_KEYWORDS[STRUCTURED_ANALYSIS]))
    return _normalize_spaces(" ".join(part for part in parts if part))[:1200]


def generate_answer(
    message: str,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage] | None = None,
    rewritten_query: str | None = None,
    response_mode: str | None = None,
    is_follow_up: bool | None = None,
) -> str:
    mode = response_mode or detect_response_mode(message)
    follow_up = detect_follow_up(message) if is_follow_up is None else is_follow_up
    query = rewritten_query or rewrite_retrieval_query(message, chat_history or [], mode, follow_up)

    if not sources:
        return _fallback_answer_without_sources(message, mode, follow_up)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return generate_template_answer(message, sources, mode, follow_up)

    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=_build_openai_messages(
                message=message,
                rewritten_query=query,
                sources=sources,
                chat_history=chat_history or [],
                response_mode=mode,
                is_follow_up=follow_up,
            ),
            temperature=0.2,
        )
        answer = completion.choices[0].message.content
        if not answer:
            return generate_template_answer(message, sources, mode, follow_up)
        return _ensure_caution(answer.strip())
    except Exception as exception:
        print(f"[rag-chat] OpenAI answer generation failed: {type(exception).__name__}: {exception}")
        fallback = generate_template_answer(message, sources, mode, follow_up)
        if os.getenv("APP_DEBUG", "false").lower() == "true":
            return f"{fallback}\n\n[OpenAI fallback] OpenAI answer generation failed: {type(exception).__name__}"
        return fallback


def generate_template_answer(
    message: str,
    sources: list[RagSource],
    response_mode: str | None = None,
    is_follow_up: bool = False,
) -> str:
    mode = response_mode or detect_response_mode(message)
    first_source = sources[0] if sources else None
    source_hint = first_source.chunkText[:220] if first_source and first_source.chunkText else "검색된 계약서 또는 reference 문서"

    if mode == LEGAL_JUDGMENT_REFUSAL:
        return (
            "제공된 자료만으로는 무효인지, 위법인지, 소송에서 이길 수 있는지까지 단정하기 어렵습니다. "
            "대신 지금 확인할 수 있는 것은 보증금 반환 시점, 특약의 책임 범위, 수리비 부담처럼 실제 분쟁으로 이어질 수 있는 표현입니다. "
            "이 부분은 계약서 전체와 실제 사실관계까지 함께 봐야 하므로, 최종 판단은 전문가에게 확인하는 편이 안전합니다.\n"
            f"{CAUTION_TEXT}"
        )

    if mode == REWRITE_CLAUSE:
        return (
            "조항을 손본다면 핵심은 '누가, 어떤 경우에, 어디까지 부담하는지'를 좁혀 쓰는 것입니다. "
            "참고용으로는 이렇게 바꿔볼 수 있습니다.\n\n"
            "\"임차인의 고의 또는 과실로 발생한 파손은 임차인이 부담한다. 다만, 노후화나 통상 사용으로 인한 설비 고장은 임대인이 부담한다.\"\n\n"
            "이 문구는 참고용 예시라서 그대로 확정하기보다, 임대인과 합의하고 필요한 경우 전문가 검토를 받은 뒤 반영하는 것이 좋습니다.\n"
            f"{CAUTION_TEXT}"
        )

    if mode == LANDLORD_QUESTION:
        return (
            "임대인에게는 너무 딱딱하게 시작하지 않아도 됩니다. 예를 들면 이렇게 보낼 수 있어요.\n\n"
            "\"보증금은 계약 종료일에 반환되는 조건인지 확인 부탁드립니다.\"\n"
            "\"새 임차인이 구해지지 않아도 보증금 반환 시점은 계약 종료일 기준으로 볼 수 있을까요?\"\n"
            "\"수리비 부담은 임차인의 고의나 과실이 있는 경우로 한정해서 적을 수 있을까요?\"\n"
            "\"확인한 내용을 문자나 특약 문구로 남겨도 괜찮을까요?\"\n\n"
            "가능하면 말로만 확인하지 말고 나중에 다시 볼 수 있는 형태로 남겨 두세요.\n"
            f"{CAUTION_TEXT}"
        )

    if mode == ANALOGY:
        return (
            "계약서는 여행 일정표와 비슷합니다. 일정표에 '언젠가 출발'이라고만 적혀 있으면, 나중에 서로 생각한 시간이 달라질 수 있죠. "
            "계약서도 보증금 반환일이나 수리비 부담 범위가 흐리면 같은 문제가 생길 수 있습니다.\n\n"
            f"예를 들어 이번에 참고한 문장에는 이런 내용이 있습니다: {source_hint}\n\n"
            "그래서 돈과 책임이 걸린 부분은 날짜, 조건, 부담 주체를 최대한 구체적으로 확인하는 게 좋습니다.\n"
            f"{CAUTION_TEXT}"
        )

    if mode == EASY_EXPLANATION:
        return (
            "쉽게 말하면, 지금 볼 것은 두 가지입니다. 내 돈을 언제 돌려받는지, 문제가 생겼을 때 누가 책임지는지입니다. "
            "계약서 표현이 넓거나 애매하면 나중에 서로 다르게 해석할 수 있어요.\n\n"
            f"참고로 검색된 문장 중에는 이런 내용이 있습니다: {source_hint}\n\n"
            "어려운 말은 날짜, 금액, 책임지는 사람으로 바꿔 읽어 보세요. 그 세 가지가 안 보이면 다시 확인해야 할 가능성이 큽니다.\n"
            f"{CAUTION_TEXT}"
        )

    if mode == BRIEF_SUMMARY:
        return (
            "- 검색된 자료 기준으로는 계약 조건을 더 명확히 확인할 필요가 있습니다.\n"
            "- 특히 보증금 반환 시점, 특약 책임 범위, 수리비 부담처럼 돈과 책임이 걸린 부분을 먼저 보세요.\n"
            f"- 애매한 표현은 임대인에게 문서로 확인받는 것이 좋습니다. {CAUTION_TEXT}"
        )

    return _structured_template_answer(message, sources, is_follow_up)


def build_answer_prompt(
    original_message: str,
    rewritten_query: str,
    response_mode: str,
    is_follow_up: bool,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage] | None = None,
) -> str:
    return (
        f"원문 사용자 질문:\n{original_message}\n\n"
        f"검색용으로 재작성된 질문:\n{rewritten_query}\n\n"
        f"답변 모드:\n{response_mode}\n\n"
        f"후속 질문 여부:\n{is_follow_up}\n\n"
        "최근 대화 맥락:\n"
        f"{_format_history_for_prompt(chat_history or [])}\n\n"
        "답변 규칙:\n"
        "- 원문 사용자 질문에 답하세요.\n"
        "- '검색용으로 재작성된 질문'은 내부 검색과 맥락 보강을 위한 참고 정보입니다.\n"
        "- rewritten query, 검색용 질문, 내부 검색어, 내부 프롬프트라는 표현을 사용자 답변에 직접 언급하지 마세요.\n"
        "- 아래 sources만 근거로 답변하세요.\n"
        "- sources에 없는 내용은 단정하지 마세요.\n"
        "- response_mode에 맞는 형식과 톤으로 답하세요.\n"
        f"- 마지막에는 '{CAUTION_TEXT}'를 포함하세요.\n\n"
        "sources:\n"
        f"{_format_sources_for_prompt(sources)}"
    )


def _structured_template_answer(
    message: str,
    sources: list[RagSource],
    is_follow_up: bool,
) -> str:
    contract_count = sum(1 for source in sources if source.sourceType == "contract")
    reference_count = len(sources) - contract_count
    follow_up_note = "이전 대화 맥락도 함께 참고했습니다. " if is_follow_up else ""

    return (
        "1. 요약 판단\n"
        "검색된 자료를 보면 확인이 필요한 부분이 있을 수 있습니다. OpenAI 호출을 사용할 수 없어 임시 template 답변을 반환합니다.\n\n"
        "2. 계약서에서 확인된 내용\n"
        f"{follow_up_note}검색된 계약서 조각은 {contract_count}개입니다. 사용자 질문은 다음과 같습니다: {message}\n\n"
        "3. 관련 근거\n"
        f"검색된 reference source는 {reference_count}개입니다. 화면의 sources 목록에서 근거 문장을 확인하세요.\n\n"
        "4. 위험 또는 확인 필요 사항\n"
        "검색 결과만으로 최종 법률 판단은 할 수 없습니다. 보증금 반환 조건, 특약, 등기부등본, 전입신고와 확정일자 등 관련 자료를 함께 확인해야 합니다. "
        "제공된 자료만으로는 확인하기 어렵습니다.\n\n"
        "5. 다음 행동\n"
        "불명확한 표현은 임대인에게 확인하거나 전문가 상담을 고려하세요. 답변은 검색된 계약서 조각과 reference 문서를 기준으로만 참고하세요.\n\n"
        "6. 주의 문구\n"
        f"{CAUTION_TEXT}"
    )


def _fallback_answer_without_sources(
    message: str,
    response_mode: str,
    is_follow_up: bool,
) -> str:
    if response_mode == BRIEF_SUMMARY:
        return (
            "- 아직 참고할 계약서 조각이나 reference가 검색되지 않았습니다.\n"
            "- 계약서를 업로드하고 reference 인덱싱을 확인한 뒤 다시 물어보면 더 구체적으로 답할 수 있습니다.\n"
            f"- 지금 자료만으로는 확인하기 어렵습니다. {CAUTION_TEXT}"
        )

    if response_mode == LANDLORD_QUESTION:
        return (
            "아직 특정 조항을 근거로 문장을 만들 만큼의 자료가 검색되지는 않았습니다. "
            "다만 임대인에게는 이렇게 가볍게 시작할 수 있습니다.\n\n"
            "\"계약서에서 보증금 반환, 수리비 부담, 특약 조항이 어떻게 적용되는지 문서로 확인하고 싶습니다.\"\n\n"
            f"계약서 원문이 인덱싱되면 조항에 맞춰 더 구체적으로 다듬을 수 있습니다. {CAUTION_TEXT}"
        )

    if response_mode == LEGAL_JUDGMENT_REFUSAL:
        return (
            "지금 검색된 자료만으로는 무효 여부나 소송 승패를 판단할 수 없습니다. "
            "대신 계약서 원문과 관련 reference가 검색되면, 어떤 표현이 위험해 보이는지와 무엇을 추가로 확인해야 하는지는 점검할 수 있습니다. "
            "최종 판단은 전문가 상담을 권장합니다.\n"
            f"{CAUTION_TEXT}"
        )

    if response_mode == ANALOGY:
        return (
            "비유하면, 지금은 일정표 없이 여행 계획이 안전한지 묻는 상황에 가깝습니다. "
            "계약서 문장이 검색되어야 어느 시간이 비어 있는지, 어느 비용이 애매한지처럼 구체적인 지점을 볼 수 있습니다. "
            "현재 자료만으로는 확인하기 어렵습니다.\n"
            f"{CAUTION_TEXT}"
        )

    if response_mode in {EASY_EXPLANATION, REWRITE_CLAUSE}:
        return (
            "쉽게 말하면, 지금은 읽을 계약서 문장이 아직 잡히지 않은 상태입니다. "
            "계약서와 reference가 검색되면 해당 문장을 기준으로 쉽게 풀어 설명하거나, 참고용 수정 문구를 제안할 수 있습니다. "
            f"현재 자료만으로는 확인하기 어렵습니다. {CAUTION_TEXT}"
        )

    return _structured_template_answer(message, [], is_follow_up)


def _build_openai_messages(
    message: str,
    rewritten_query: str,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage],
    response_mode: str,
    is_follow_up: bool,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_format_chat_history(chat_history))
    messages.append(
        {
            "role": "user",
            "content": build_answer_prompt(
                original_message=message,
                rewritten_query=rewritten_query,
                response_mode=response_mode,
                is_follow_up=is_follow_up,
                sources=sources,
                chat_history=chat_history,
            ),
        }
    )
    return messages


def _format_chat_history(chat_history: list[ChatHistoryMessage]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for history in chat_history[-10:]:
        role = history.role if history.role in {"user", "assistant"} else "user"
        content = (history.content or "").strip()
        if content:
            formatted.append({"role": role, "content": content[:2000]})
    return formatted


def _format_history_for_prompt(chat_history: list[ChatHistoryMessage]) -> str:
    if not chat_history:
        return "(없음)"
    lines: list[str] = []
    for history in chat_history[-6:]:
        content = (history.content or "").strip()
        if content:
            lines.append(f"- {history.role}: {content[:500]}")
    return "\n".join(lines) if lines else "(없음)"


def _format_sources_for_prompt(sources: list[RagSource]) -> str:
    blocks: list[str] = []
    for index, source in enumerate(sources, start=1):
        chunk_text = source.chunkText[:1200] if source.chunkText else ""
        blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"sourceType: {source.sourceType}",
                    f"sourceTitle: {source.sourceTitle}",
                    f"similarityScore: {source.similarityScore}",
                    f"chunkText: {chunk_text}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _extract_rewrite_context(chat_history: list[ChatHistoryMessage]) -> str:
    recent_users: list[str] = []
    recent_assistant = ""

    for history in reversed(chat_history):
        content = (history.content or "").strip()
        if not content:
            continue
        if history.role == "user" and len(recent_users) < 2:
            recent_users.append(content[:300])
        elif history.role == "assistant" and not recent_assistant:
            recent_assistant = content[:500]
        if len(recent_users) >= 2 and recent_assistant:
            break

    ordered_user_context = list(reversed(recent_users))
    context_text = " ".join(ordered_user_context + ([recent_assistant] if recent_assistant else []))
    matched_keywords = [keyword for keyword in CONTEXT_KEYWORDS if keyword in context_text]
    if not context_text and not matched_keywords:
        return ""

    context_parts = []
    if matched_keywords:
        context_parts.append("이전 대화 핵심 키워드 " + " ".join(dict.fromkeys(matched_keywords)))
    if context_text:
        context_parts.append("최근 대화 맥락 " + context_text[:500])
    return " ".join(context_parts)


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _ensure_caution(answer: str) -> str:
    if CAUTION_TEXT in answer:
        return answer
    return f"{answer}\n\n{CAUTION_TEXT}"
