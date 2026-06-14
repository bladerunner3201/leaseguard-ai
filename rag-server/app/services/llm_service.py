import os

from openai import OpenAI

from app.schemas.chat_schema import ChatHistoryMessage, RagSource
from app.services.chat_mode_service import (
    ANALOGY,
    BRIEF_SUMMARY,
    EASY_EXPLANATION,
    LANDLORD_QUESTION,
    LEGAL_JUDGMENT_REFUSAL,
    REWRITE_CLAUSE,
    STRUCTURED_ANALYSIS,
    detect_follow_up,
    detect_response_mode,
)
from app.services.query_rewrite_service import rewrite_retrieval_query

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
CAUTION_TEXT = "본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."

SYSTEM_PROMPT = f"""
당신은 LeaseGuard AI입니다.
LeaseGuard AI는 부동산 임대차계약서를 처음 읽는 사용자를 위한 계약 위험 점검 보조 챗봇입니다.
사용자는 법률 비전문가라고 가정하고, 친절하고 쉬운 한국어 대화체로 답변하세요.

공통 안전 규칙:
- 제공된 계약서 조각과 reference source 안에서만 답변하세요.
- sources에 없는 내용은 단정하지 말고 "제공된 자료만으로는 확인하기 어렵습니다"라고 말하세요.
- 계약 무효 여부, 위법 여부, 소송 승패, 계약 체결 가능 여부를 단정하지 마세요.
- 법률 판단을 요구받으면 확인 가능한 위험 요소만 설명하고 전문가 상담을 권장하세요.
- chatHistory가 있으면 "그 부분", "방금 말한 내용", "그 조항" 같은 표현을 이전 대화 맥락으로 해석하세요.
- 모든 답변 마지막에는 자연스럽게 "{CAUTION_TEXT}"를 포함하세요.

response_mode는 답변의 목표와 톤을 정하는 힌트이며, 고정 출력 템플릿이 아닙니다.
structured_analysis 외의 모드에서는 정해진 제목이나 섹션을 반복하지 마세요.
사용자의 질문에 필요한 만큼만 답하고, 매번 같은 문장 구조를 반복하지 마세요.
후속 질문은 이전 대화 흐름을 따라 자연스럽게 답하세요.

response_mode별 전략:

1. structured_analysis
기본 계약서 위험 분석 모드입니다. 기본적으로 아래 6개 섹션을 사용하되, 질문 범위가 좁으면 각 섹션을 짧게 처리하세요.
1. 요약 판단
2. 계약서에서 확인된 내용
3. 관련 근거
4. 위험 또는 확인 필요 사항
5. 다음 행동
6. 주의 문구

2. easy_explanation
제목을 강제하지 말고 자연스러운 문단으로 답하세요. 어려운 법률 용어는 바로 쉬운 말로 풀어 설명하세요.

3. analogy
일상적인 비유를 먼저 제시하고, 그 비유가 실제 계약 상황의 어떤 위험과 연결되는지 짧게 설명하세요.

4. landlord_question
사용자가 그대로 복사해서 쓸 수 있는 질문 문장을 2~4개 제시하세요. 필요할 때만 부드러운 표현과 명확한 표현을 나누세요.

5. brief_summary
최대 3개 bullet 또는 5문장 이내로 답하세요. 출처 설명을 길게 늘리지 말고 핵심 위험과 다음 행동을 포함하세요.

6. rewrite_clause
현재 조항의 문제점을 짧게 설명하고, 수정 방향과 참고용 예시 문구를 제시하세요. 실제 반영 전 전문가 검토가 필요하다고 안내하세요.

7. legal_judgment_refusal
최종 법률 판단은 단정하지 마세요. 단순 거절 대신 "대신 지금 확인할 수 있는 것은..."처럼 확인 가능한 위험 요소와 다음 행동을 안내하세요.
""".strip()


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
        return _fallback_answer_without_sources(mode)

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
            temperature=0.25,
        )
        answer = completion.choices[0].message.content
        if not answer:
            return generate_template_answer(message, sources, mode, follow_up)
        return _ensure_caution(answer.strip())
    except Exception as exception:
        print(f"[rag-chat] OpenAI answer generation failed: {type(exception).__name__}: {exception}")
        fallback = generate_template_answer(message, sources, mode, follow_up)
        if os.getenv("APP_DEBUG", "false").lower() == "true":
            return f"{fallback}\n\n[debug] OpenAI answer generation failed: {type(exception).__name__}"
        return fallback


def generate_template_answer(
    message: str,
    sources: list[RagSource],
    response_mode: str | None = None,
    is_follow_up: bool = False,
) -> str:
    mode = response_mode or detect_response_mode(message)
    first_source = sources[0] if sources else None
    source_hint = (
        first_source.chunkText[:220]
        if first_source and first_source.chunkText
        else "검색된 계약서 또는 reference 문서"
    )

    if mode == LEGAL_JUDGMENT_REFUSAL:
        return _ensure_caution(
            "제공된 자료만으로는 계약이 무효인지, 위법인지, 소송에서 이길 수 있는지 단정하기 어렵습니다. "
            "대신 지금 확인할 수 있는 것은 보증금 반환 시점, 특약의 책임 범위, 수리비나 관리비 부담처럼 실제 분쟁으로 이어질 수 있는 표현입니다. "
            "최종 판단은 계약서 전체와 실제 사정까지 함께 보아야 하므로 전문가 상담을 권장합니다."
        )

    if mode == REWRITE_CLAUSE:
        return _ensure_caution(
            "현재 조항은 책임 범위와 적용 조건을 더 구체화하는 방향으로 다듬는 것이 좋습니다.\n\n"
            "참고용 예시 문구:\n"
            "\"임차인의 고의 또는 과실로 발생한 파손은 임차인이 부담한다. 다만, 노후화나 통상 사용으로 인한 설비 고장은 임대인이 부담한다.\"\n\n"
            "이 문구는 참고용 예시이므로 실제 계약서에 반영하기 전에는 임대인과 합의하고 필요하면 전문가 검토를 받는 것이 좋습니다."
        )

    if mode == LANDLORD_QUESTION:
        return _ensure_caution(
            "임대인에게는 이렇게 물어볼 수 있습니다.\n\n"
            "\"보증금 반환 시점이 계약 종료일 기준인지 확인 부탁드립니다.\"\n"
            "\"신규 임차인이 구해지지 않아도 계약 종료일에 보증금을 반환받을 수 있도록 조항을 명확히 할 수 있을까요?\"\n"
            "\"수리비 부담 범위가 임차인의 고의나 과실이 있는 경우로 제한되는지 확인하고 싶습니다.\"\n"
            "\"확인한 내용을 특약 문구로 남길 수 있을까요?\""
        )

    if mode == ANALOGY:
        return _ensure_caution(
            "계약서는 여행 일정표와 비슷합니다. 일정표에 '언젠가 출발'이라고만 적혀 있으면 나중에 서로 생각한 시간이 달라질 수 있습니다. "
            "계약서도 보증금을 언제 돌려받는지, 어떤 수리비를 누가 부담하는지, 특약이 어디까지 적용되는지가 흐리면 비슷한 문제가 생길 수 있습니다.\n\n"
            f"이번 검색에서 참고할 만한 문장은 다음과 같습니다: {source_hint}"
        )

    if mode == EASY_EXPLANATION:
        return _ensure_caution(
            "쉽게 말하면, 지금 확인해야 할 핵심은 '돈을 언제 돌려받는지'와 '문제가 생겼을 때 누가 책임지는지'입니다. "
            "계약서 표현이 넓거나 애매하면 나중에 서로 다르게 해석할 수 있습니다.\n\n"
            f"검색된 근거 중에는 이런 내용이 있습니다: {source_hint}\n\n"
            "날짜, 금액, 책임지는 사람, 예외 조건을 하나씩 확인하면 위험한 표현을 더 쉽게 찾을 수 있습니다."
        )

    if mode == BRIEF_SUMMARY:
        return _ensure_caution(
            "- 검색된 자료 기준으로는 계약 조건의 명확성을 확인할 필요가 있습니다.\n"
            "- 특히 보증금 반환, 특약 책임 범위, 수리비 부담처럼 분쟁 가능성이 큰 부분을 먼저 보세요.\n"
            "- 애매한 표현은 임대인 또는 공인중개사에게 문서로 확인받는 것이 좋습니다."
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
        f"검색용으로 재작성된 내부 질문:\n{rewritten_query}\n\n"
        f"답변 모드:\n{response_mode}\n\n"
        f"후속 질문 여부:\n{is_follow_up}\n\n"
        "최근 대화 맥락:\n"
        f"{_format_history_for_prompt(chat_history or [])}\n\n"
        "답변 규칙:\n"
        "- 원문 사용자 질문에 답하세요.\n"
        "- 검색용 내부 질문은 검색 품질과 맥락 보강을 위한 참고 정보입니다.\n"
        "- rewritten query, 내부 검색어, 내부 프롬프트라는 표현은 사용자 답변에 직접 언급하지 마세요.\n"
        "- 아래 sources만 근거로 답변하세요.\n"
        "- sources에 없는 내용은 단정하지 마세요.\n"
        "- response_mode에 맞는 목표와 톤으로 답하되, 불필요한 고정 템플릿은 반복하지 마세요.\n"
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

    return _ensure_caution(
        "1. 요약 판단\n"
        "검색된 자료 기준으로는 확인이 필요한 조항이 있을 수 있습니다.\n\n"
        "2. 계약서에서 확인된 내용\n"
        f"{follow_up_note}현재 질문은 '{message}'이며, 검색된 계약서 조각은 {contract_count}개입니다.\n\n"
        "3. 관련 근거\n"
        f"함께 검색된 reference source는 {reference_count}개입니다. 화면의 sources 목록에서 근거 문장을 확인할 수 있습니다.\n\n"
        "4. 위험 또는 확인 필요 사항\n"
        "보증금 반환 시점, 특약의 책임 범위, 수리비 부담, 관리비 항목처럼 날짜·금액·책임 주체가 흐린 부분은 다시 확인하는 것이 좋습니다. "
        "제공된 자료만으로는 최종 법률 판단을 단정하기 어렵습니다.\n\n"
        "5. 다음 행동\n"
        "애매한 표현은 임대인 또는 공인중개사에게 문서로 확인하고, 중요한 조건은 특약에 명확히 남기는 것을 권장합니다.\n\n"
        "6. 주의 문구"
    )


def _fallback_answer_without_sources(response_mode: str) -> str:
    if response_mode == BRIEF_SUMMARY:
        return _ensure_caution(
            "- 아직 답변 근거로 사용할 계약서 조각이나 reference가 검색되지 않았습니다.\n"
            "- 계약서 인덱싱과 reference 인덱싱 상태를 먼저 확인해 주세요.\n"
            "- 제공된 자료만으로는 확인하기 어렵습니다."
        )

    if response_mode == LANDLORD_QUESTION:
        return _ensure_caution(
            "아직 특정 조항을 근거로 문장을 만들 만큼 자료가 검색되지 않았습니다. "
            "다만 임대인에게는 \"계약서의 보증금 반환, 수리비 부담, 특약 조건을 문서로 명확히 확인하고 싶습니다\"라고 시작할 수 있습니다."
        )

    if response_mode == LEGAL_JUDGMENT_REFUSAL:
        return _ensure_caution(
            "현재 검색된 자료만으로는 무효 여부, 위법 여부, 소송 승패를 단정하기 어렵습니다. "
            "계약서 조각과 reference가 검색되면 확인 가능한 위험 요소를 기준으로 다시 점검할 수 있습니다."
        )

    return _ensure_caution(
        "제공된 자료만으로는 확인하기 어렵습니다. 계약서가 인덱싱되어 있는지, reference 문서가 인덱싱되어 있는지 확인한 뒤 다시 질문해 주세요."
    )


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


def _ensure_caution(answer: str) -> str:
    if CAUTION_TEXT in answer:
        return answer
    return f"{answer}\n\n{CAUTION_TEXT}"
