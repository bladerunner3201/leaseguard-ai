import os

from openai import OpenAI

from app.schemas.chat_schema import ChatHistoryMessage, RagSource
from app.services.chat_mode_service import (
    ANALOGY,
    BRIEF_SUMMARY,
    ChatIntent,
    EASY_EXPLANATION,
    LANDLORD_QUESTION,
    LEGAL_JUDGMENT_REFUSAL,
    REWRITE_CLAUSE,
    SAFETY_LEGAL_JUDGMENT_SENSITIVE,
    STRUCTURED_ANALYSIS,
    detect_chat_intent,
    detect_follow_up,
    detect_response_mode,
)
from app.services.query_rewrite_service import rewrite_retrieval_query

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
CAUTION_TEXT = "본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."

SYSTEM_PROMPT = f"""
당신은 LeaseGuard AI이다.
LeaseGuard AI는 부동산 임대차계약서를 처음 읽는 사용자를 위한 계약 위험 점검 보조 챗봇이다.
사용자는 법률 비전문가라고 가정하고, 친절하고 쉬운 한국어 대화체로 답한다.

공통 안전 규칙:
- 제공된 계약서 조각과 reference source 안에서만 답한다.
- sources에 없는 내용은 단정하지 말고 "제공된 자료만으로는 확인하기 어렵습니다"라고 말한다.
- 계약 무효 여부, 위법 여부, 소송 승패, 계약 체결 가능 여부를 단정하지 않는다.
- 법률 판단을 요구받으면 확인 가능한 위험 요소만 설명하고 전문가 상담을 권장한다.
- 계약서나 reference 근거를 언급하는 핵심 문장에는 [Source 1], [Source 2]처럼 제공된 source 번호를 붙인다.
- source 번호는 prompt에 제공된 sources 순서를 그대로 따른다. 존재하지 않는 번호를 만들지 않는다.
- chatHistory가 있으면 "그 부분", "방금 말한 내용", "그 조항" 같은 표현을 이전 대화 흐름으로 해석한다.
- 모든 답변 마지막에는 자연스럽게 "{CAUTION_TEXT}"를 포함한다.

구조화된 intent 사용 원칙:
- topic, answerStyle, safetyLevel, isFollowUp은 내부 답변 전략을 정하기 위한 힌트이다.
- 이 intent 값 자체를 사용자에게 직접 설명하지 않는다.
- answerStyle이 structured_analysis인 경우에만 기본 6개 섹션 형식을 사용한다.
- structured_analysis에서도 질문 범위가 좁으면 각 섹션은 짧게 처리한다.
- structured_analysis 외의 스타일에서는 정해진 제목이나 섹션을 반복하지 않는다.
- 사용자의 질문에 필요한 만큼만 답하고, 매번 같은 문장 구조를 반복하지 않는다.
- 후속 질문은 이전 대화 흐름을 따라 자연스럽게 답한다.

answerStyle별 전략:
- structured_analysis: 기본 계약서 위험 분석 모드이다. "요약 판단, 계약서에서 확인된 내용, 관련 근거, 위험 또는 확인 필요 사항, 다음 행동, 주의 문구" 형식을 기본으로 한다.
- easy_explanation: 제목을 강제하지 않고 쉬운 문단으로 답한다. 어려운 법률 용어는 바로 풀어서 설명한다.
- analogy: 일상적인 비유를 먼저 제시하고, 그 비유를 실제 계약 상황 및 확인할 점과 연결한다.
- landlord_question: 사용자가 임대인에게 바로 보낼 수 있는 질문 문장 2~4개를 제시한다. 필요할 때만 부드러운 표현과 명확한 표현을 나눈다.
- brief_summary: 최대 3개 bullet 또는 5문장 이내로 답한다. 출처 설명을 길게 늘리지 않는다.
- rewrite_clause: 현재 조항의 문제점, 수정 방향, 참고용 예시 문구를 제시한다. 실제 반영 전 전문가 검토가 필요하다고 안내한다.

safetyLevel별 전략:
- normal: 일반 위험 점검으로 답한다.
- legal_judgment_sensitive: 단정하지 않되 단순 거절로 끝내지 않는다. "대신 지금 확인할 수 있는 것은..."처럼 확인 가능한 위험 요소와 다음 행동을 안내한다.
""".strip()


def generate_answer(
    message: str,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage] | None = None,
    rewritten_query: str | None = None,
    response_mode: str | None = None,
    is_follow_up: bool | None = None,
    chat_intent: ChatIntent | None = None,
) -> str:
    intent = chat_intent or detect_chat_intent(message)
    mode = response_mode or intent.response_mode
    follow_up = intent.isFollowUp if is_follow_up is None else is_follow_up
    query = rewritten_query or rewrite_retrieval_query(
        message=message,
        chat_history=chat_history or [],
        response_mode=mode,
        is_follow_up=follow_up,
        chat_intent=intent,
    )

    if not sources:
        return _fallback_answer_without_sources(intent)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return generate_template_answer(message, sources, chat_intent=intent)

    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=_build_openai_messages(
                message=message,
                rewritten_query=query,
                sources=sources,
                chat_history=chat_history or [],
                chat_intent=intent,
                response_mode=mode,
                is_follow_up=follow_up,
            ),
            temperature=0.25,
        )
        answer = completion.choices[0].message.content
        if not answer:
            return generate_template_answer(message, sources, chat_intent=intent)
        return _ensure_caution(answer.strip())
    except Exception as exception:
        print(f"[rag-chat] OpenAI answer generation failed: {type(exception).__name__}: {exception}")
        fallback = generate_template_answer(message, sources, chat_intent=intent)
        if os.getenv("APP_DEBUG", "false").lower() == "true":
            return f"{fallback}\n\n[debug] OpenAI answer generation failed: {type(exception).__name__}"
        return fallback


def generate_template_answer(
    message: str,
    sources: list[RagSource],
    response_mode: str | None = None,
    is_follow_up: bool = False,
    chat_intent: ChatIntent | None = None,
) -> str:
    intent = chat_intent or detect_chat_intent(message)
    mode = response_mode or intent.response_mode
    follow_up = intent.isFollowUp or is_follow_up
    first_source = sources[0] if sources else None
    source_ref = "[Source 1]" if first_source else ""
    source_hint = (
        first_source.chunkText[:220]
        if first_source and first_source.chunkText
        else "검색된 계약서 또는 reference 문서"
    )

    if intent.safetyLevel == SAFETY_LEGAL_JUDGMENT_SENSITIVE or mode == LEGAL_JUDGMENT_REFUSAL:
        return _ensure_caution(
            "제공된 자료만으로는 계약이 무효인지, 위법인지, 소송에서 이길 수 있는지 단정하기 어렵습니다. "
            f"대신 지금 확인할 수 있는 것은 보증금 반환 시점, 특약의 책임 범위, 수리비나 관리비 부담처럼 실제 분쟁으로 이어질 수 있는 표현입니다. {source_ref} "
            "최종 판단은 계약서 전체와 실제 사정을 함께 봐야 하므로 변호사나 공인중개사 등 전문가 상담을 권장합니다."
        )

    if mode == REWRITE_CLAUSE:
        return _ensure_caution(
            "현재 조항은 책임 범위와 적용 조건을 더 구체화하는 방향으로 다듬는 것이 좋습니다.\n\n"
            "참고용 예시 문구:\n"
            "\"임차인의 고의 또는 과실로 발생한 파손은 임차인이 부담한다. 다만, 노후화나 통상 사용으로 인한 설비 고장은 임대인이 부담한다.\"\n\n"
            f"이 문구는 참고용이며, 실제 계약서 반영 전 임대인과 합의하고 필요하면 전문가 검토를 받는 것이 좋습니다. {source_ref}"
        )

    if mode == LANDLORD_QUESTION:
        return _ensure_caution(
            "임대인에게는 이렇게 물어볼 수 있습니다.\n\n"
            "\"보증금 반환 시점이 계약 종료일 기준인지 확인 부탁드립니다.\"\n"
            "\"신규 임차인이 구해지지 않아도 계약 종료일에 보증금을 반환받을 수 있도록 조항을 명확히 할 수 있을까요?\"\n"
            "\"수리비 부담 범위가 임차인의 고의나 과실이 있는 경우로 제한되는지 확인하고 싶습니다.\"\n"
            f"\"확인한 내용을 특약 문구로 남길 수 있을까요?\" {source_ref}"
        )

    if mode == ANALOGY:
        return _ensure_caution(
            "계약서는 여행 일정표와 비슷합니다. 일정표에 '언젠가 출발'이라고만 적혀 있으면 사람마다 생각하는 출발 시간이 달라질 수 있습니다. "
            "계약서도 보증금을 언제 돌려받는지, 어떤 수리비를 누가 부담하는지, 특약이 어디까지 적용되는지가 흐리면 나중에 해석이 갈릴 수 있습니다.\n\n"
            f"이번 검색에서 참고할 만한 문장은 다음과 같습니다: {source_hint} {source_ref}"
        )

    if mode == EASY_EXPLANATION:
        return _ensure_caution(
            "쉽게 말하면, 지금 확인할 핵심은 '돈을 언제 돌려받는지'와 '문제가 생겼을 때 누가 책임지는지'입니다. "
            "계약서 표현이 넓거나 애매하면 나중에 서로 다르게 해석할 수 있습니다.\n\n"
            f"검색된 근거 중에는 이런 내용이 있습니다: {source_hint} {source_ref} "
            "날짜, 금액, 책임지는 사람, 예외 조건을 하나씩 확인하면 위험한 표현을 더 쉽게 찾을 수 있습니다."
        )

    if mode == BRIEF_SUMMARY:
        return _ensure_caution(
            f"- 검색된 자료 기준으로 계약 조건의 명확성을 확인할 필요가 있습니다. {source_ref}\n"
            "- 특히 보증금 반환, 특약 책임 범위, 수리비 부담처럼 분쟁 가능성이 있는 부분을 먼저 보세요.\n"
            "- 애매한 표현은 임대인 또는 공인중개사에게 문서로 확인받는 것이 좋습니다."
        )

    return _structured_template_answer(message, sources, follow_up)


def build_answer_prompt(
    original_message: str,
    rewritten_query: str,
    response_mode: str,
    is_follow_up: bool,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage] | None = None,
    chat_intent: ChatIntent | None = None,
) -> str:
    intent = chat_intent or detect_chat_intent(original_message)
    return (
        f"원문 사용자 질문:\n{original_message}\n\n"
        "구조화된 의도:\n"
        f"- topic: {intent.topic}\n"
        f"- answerStyle: {intent.answerStyle}\n"
        f"- safetyLevel: {intent.safetyLevel}\n"
        f"- isFollowUp: {intent.isFollowUp}\n"
        f"- compatibilityResponseMode: {response_mode}\n\n"
        f"검색용으로 재작성된 내부 질문:\n{rewritten_query}\n\n"
        "중요:\n"
        "- 구조화된 의도와 rewritten query는 내부 참고용이다.\n"
        "- 사용자에게 topic, answerStyle, safetyLevel, response_mode, rewritten query라는 표현을 직접 말하지 않는다.\n"
        "- 원문 사용자 질문에 자연스럽게 답한다.\n"
        "- 아래 sources만 근거로 답한다.\n"
        "- sources에 없는 내용은 단정하지 않는다.\n"
        "- 계약서나 reference 근거를 언급하는 핵심 문장에는 [Source 1], [Source 2]처럼 source 번호를 붙인다.\n"
        "- source 번호는 아래 sources 목록의 번호와 정확히 일치해야 한다.\n"
        f"- 마지막에는 '{CAUTION_TEXT}'를 포함한다.\n\n"
        f"후속 질문 여부:\n{is_follow_up}\n\n"
        "최근 대화 맥락:\n"
        f"{_format_history_for_prompt(chat_history or [])}\n\n"
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

    return _ensure_caution(
        "1. 요약 판단\n"
        "검색된 자료 기준으로는 확인이 필요한 계약 조건이 있을 수 있습니다.\n\n"
        "2. 계약서에서 확인된 내용\n"
        f"{follow_up_note}현재 질문은 '{message}'이며, 검색된 계약서 조각은 {contract_count}개입니다.\n\n"
        "3. 관련 근거\n"
        f"함께 검색된 reference source는 {reference_count}개입니다. 주요 근거는 sources 목록의 번호와 연결해 확인할 수 있습니다. [Source 1]\n\n"
        "4. 위험 또는 확인 필요 사항\n"
        "보증금 반환 시점, 특약의 책임 범위, 수리비 부담, 관리비 항목처럼 날짜, 금액, 책임 주체가 애매한 부분을 다시 확인하는 것이 좋습니다. [Source 1]\n\n"
        "5. 다음 행동\n"
        "애매한 표현은 임대인 또는 공인중개사에게 문서로 확인하고, 중요한 조건은 특약에 명확히 남기는 것을 권장합니다.\n\n"
        "6. 주의 문구"
    )


def _fallback_answer_without_sources(intent: ChatIntent) -> str:
    if intent.safetyLevel == SAFETY_LEGAL_JUDGMENT_SENSITIVE:
        return _ensure_caution(
            "현재 검색된 근거가 없어 무효 여부, 위법 여부, 소송 승패를 단정하기 어렵습니다. "
            "계약서 인덱싱 상태와 reference 문서 검색 상태를 먼저 확인한 뒤, 확인 가능한 위험 요소를 기준으로 다시 점검하는 것이 좋습니다."
        )

    if intent.answerStyle == BRIEF_SUMMARY:
        return _ensure_caution(
            "- 아직 답변 근거로 사용할 계약서 조각이나 reference가 검색되지 않았습니다.\n"
            "- 계약서와 reference 인덱싱 상태를 먼저 확인해 주세요.\n"
            "- 자료가 검색되면 핵심 위험과 다음 행동을 짧게 정리할 수 있습니다."
        )

    if intent.answerStyle == LANDLORD_QUESTION:
        return _ensure_caution(
            "아직 특정 조항을 근거로 질문 문장을 만들 만큼 자료가 검색되지 않았습니다. "
            "다만 시작 문장으로는 \"계약서의 보증금 반환, 수리비 부담, 특약 조건을 문서로 명확히 확인하고 싶습니다\"라고 물어볼 수 있습니다."
        )

    return _ensure_caution(
        "제공된 자료만으로는 확인하기 어렵습니다. 계약서가 인덱싱되어 있는지, reference 문서가 검색 가능한 상태인지 확인한 뒤 다시 질문해 주세요."
    )


def _build_openai_messages(
    message: str,
    rewritten_query: str,
    sources: list[RagSource],
    chat_history: list[ChatHistoryMessage],
    chat_intent: ChatIntent,
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
                chat_intent=chat_intent,
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


def _ensure_caution(answer: str) -> str:
    if CAUTION_TEXT in answer:
        return answer
    return f"{answer}\n\n{CAUTION_TEXT}"
