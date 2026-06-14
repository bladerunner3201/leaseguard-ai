import json
import re
from typing import Any

from app.schemas.chat_schema import ChatHistoryMessage
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
    TOPIC_DEPOSIT_RETURN,
    TOPIC_GENERAL_CONTRACT_RISK,
    TOPIC_JEONSE_FRAUD_PREVENTION,
    TOPIC_MOVE_IN_FIXED_DATE,
    TOPIC_REGISTRY_CHECK,
    TOPIC_SPECIAL_CLAUSE_REPAIR,
    detect_chat_intent,
)

MEMORY_MARKER = "STRUCTURED_CHAT_MEMORY_JSON"

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

TOPIC_QUERY_KEYWORDS = {
    TOPIC_DEPOSIT_RETURN: [
        "보증금 반환",
        "반환 시점",
        "반환 지연",
        "계약 종료",
        "임차권등기명령",
    ],
    TOPIC_SPECIAL_CLAUSE_REPAIR: [
        "특약 조항",
        "불리한 조항",
        "수리비",
        "수선 의무",
        "원상복구",
        "임차인 부담",
    ],
    TOPIC_MOVE_IN_FIXED_DATE: [
        "전입신고",
        "확정일자",
        "대항력",
        "우선변제권",
        "주민등록",
    ],
    TOPIC_REGISTRY_CHECK: [
        "등기부등본",
        "근저당",
        "압류",
        "가압류",
        "선순위 권리",
        "소유자 확인",
    ],
    TOPIC_JEONSE_FRAUD_PREVENTION: [
        "전세사기 예방",
        "보증보험",
        "시세 확인",
        "전세가율",
        "깡통전세",
    ],
    TOPIC_GENERAL_CONTRACT_RISK: [
        "임대차계약서",
        "위험 요소",
        "확인사항",
        "계약 조건",
    ],
}

CATEGORY_QUERY_KEYWORDS = {
    "deposit_return": ["보증금 반환", "반환 지연", "계약 종료", "임차권등기명령"],
    "special_clause": ["특약", "불리한 조항", "임차인 부담", "계약 조건 확인"],
    "special_clause_repair": ["특약", "수리비", "원상복구", "임차인 부담"],
    "repair_cost_restoration": ["수리비", "수선 의무", "원상복구", "임차인 부담", "통상 사용"],
    "move_in_fixed_date": ["전입신고", "확정일자", "대항력", "우선변제권"],
    "registry_check": ["등기부등본", "근저당", "압류", "가압류", "선순위 권리"],
    "jeonse_fraud_prevention": ["전세사기 예방", "보증보험", "시세", "전세가율"],
    "legal_judgment_sensitive": ["법률 판단 단정 불가", "전문가 상담", "무효 여부", "소송 승패"],
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
    response_mode: str | None = None,
    is_follow_up: bool | None = None,
    chat_intent: ChatIntent | None = None,
) -> str:
    """Build an internal-only query for retrieval while preserving the original user message."""
    intent = chat_intent or detect_chat_intent(message)
    mode = response_mode or intent.response_mode
    follow_up = intent.isFollowUp if is_follow_up is None else is_follow_up
    history = chat_history or []
    memory = _extract_structured_memory(history)

    parts: list[str] = [(message or "").strip()]
    parts.append(_intent_to_query_context(intent))

    if memory and _should_use_memory(message, mode, follow_up, intent):
        memory_context = _memory_to_query_context(memory)
        if memory_context:
            parts.append(memory_context)

    if follow_up or _should_use_history_context(message, mode):
        context = _extract_recent_text_context(history)
        if context:
            parts.append(context)

    parts.extend(TOPIC_QUERY_KEYWORDS.get(intent.topic, TOPIC_QUERY_KEYWORDS[TOPIC_GENERAL_CONTRACT_RISK]))
    parts.extend(RESPONSE_MODE_QUERY_KEYWORDS.get(mode, RESPONSE_MODE_QUERY_KEYWORDS[STRUCTURED_ANALYSIS]))
    if intent.safetyLevel == SAFETY_LEGAL_JUDGMENT_SENSITIVE:
        parts.extend(CATEGORY_QUERY_KEYWORDS["legal_judgment_sensitive"])

    return _normalize_spaces(" ".join(part for part in parts if part))[:1600]


def _intent_to_query_context(intent: ChatIntent) -> str:
    return (
        f"intent topic {intent.topic} "
        f"answerStyle {intent.answerStyle} "
        f"safetyLevel {intent.safetyLevel} "
        f"isFollowUp {intent.isFollowUp}"
    )


def _extract_structured_memory(chat_history: list[ChatHistoryMessage]) -> dict[str, Any] | None:
    for history in chat_history:
        content = (history.content or "").strip()
        if MEMORY_MARKER not in content:
            continue
        json_text = content.split(MEMORY_MARKER, 1)[1].strip()
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _memory_to_query_context(memory: dict[str, Any]) -> str:
    topic = _string_value(memory.get("topic"))
    categories = _string_list(memory.get("issueCategories"))
    latest_user_concern = _string_value(memory.get("latestUserConcern"))
    next_actions = _string_list(memory.get("recommendedNextActions"))

    parts = []
    if topic:
        parts.append(f"구조화 메모리 topic {topic}")
        parts.extend(CATEGORY_QUERY_KEYWORDS.get(topic, []))
    if categories:
        parts.append("구조화 메모리 issueCategories " + " ".join(categories))
        for category in categories:
            parts.extend(CATEGORY_QUERY_KEYWORDS.get(category, []))
    if latest_user_concern:
        parts.append("최근 사용자 관심사 " + latest_user_concern[:300])
    if next_actions:
        parts.append("추천 확인 행동 " + " ".join(next_actions[:3]))
    return " ".join(parts)


def _extract_recent_text_context(chat_history: list[ChatHistoryMessage]) -> str:
    recent_users: list[str] = []
    recent_assistant = ""

    for history in reversed(chat_history):
        content = (history.content or "").strip()
        if not content or MEMORY_MARKER in content:
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


def _should_use_memory(message: str, response_mode: str, is_follow_up: bool, intent: ChatIntent) -> bool:
    normalized = message or ""
    if is_follow_up:
        return True
    if intent.topic == TOPIC_GENERAL_CONTRACT_RISK and len(normalized.strip()) <= 40:
        return True
    if len(normalized.strip()) <= 30:
        return True
    return _should_use_history_context(normalized, response_mode)


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


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
