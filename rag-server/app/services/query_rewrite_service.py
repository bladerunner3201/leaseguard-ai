import re

from app.schemas.chat_schema import ChatHistoryMessage
from app.services.chat_mode_service import (
    ANALOGY,
    BRIEF_SUMMARY,
    EASY_EXPLANATION,
    LANDLORD_QUESTION,
    LEGAL_JUDGMENT_REFUSAL,
    REWRITE_CLAUSE,
    STRUCTURED_ANALYSIS,
)

RESPONSE_MODE_QUERY_KEYWORDS = {
    STRUCTURED_ANALYSIS: [
        "위험 분석",
        "계약서 확인사항",
        "보증금 반환",
        "특약",
        "수리비",
        "계약 해지",
        "관리비",
    ],
    EASY_EXPLANATION: ["쉬운 설명", "핵심 위험", "확인사항", "법률 용어 풀이"],
    ANALOGY: ["핵심 위험", "쉬운 설명", "계약 조건", "보증금 반환", "특약", "수리비"],
    LANDLORD_QUESTION: [
        "임대인 확인 질문",
        "계약 조건 확인",
        "보증금 반환",
        "특약",
        "수리비",
        "전입신고",
        "확정일자",
    ],
    BRIEF_SUMMARY: ["핵심 요약", "주요 위험", "확인사항"],
    REWRITE_CLAUSE: [
        "조항 수정",
        "특약 문구",
        "임차인 부담",
        "임대인 의무",
        "보증금 반환 조건",
        "수리비 부담 범위",
        "원상복구 범위",
    ],
    LEGAL_JUDGMENT_REFUSAL: [
        "위험 요소",
        "단정 불가",
        "전문가 상담",
        "무효 여부",
        "위법 여부",
        "소송 승패",
        "계약 확인사항",
    ],
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


def rewrite_retrieval_query(
    message: str,
    chat_history: list[ChatHistoryMessage] | None,
    response_mode: str,
    is_follow_up: bool,
) -> str:
    """Build an internal-only query for vector retrieval while preserving the original user message."""
    parts: list[str] = [(message or "").strip()]

    if is_follow_up or _should_use_history_context(message, response_mode):
        context = _extract_rewrite_context(chat_history or [])
        if context:
            parts.append(context)

    parts.extend(RESPONSE_MODE_QUERY_KEYWORDS.get(response_mode, RESPONSE_MODE_QUERY_KEYWORDS[STRUCTURED_ANALYSIS]))
    return _normalize_spaces(" ".join(part for part in parts if part))[:1200]


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


def _should_use_history_context(message: str, response_mode: str) -> bool:
    normalized = message or ""
    style_only_markers = [
        "짧게",
        "핵심만",
        "요약",
        "비유",
        "쉽게",
        "너무 어려",
        "다시 설명",
        "예시",
    ]
    style_modes = {BRIEF_SUMMARY, ANALOGY, EASY_EXPLANATION}
    return response_mode in style_modes and any(marker in normalized for marker in style_only_markers)


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
