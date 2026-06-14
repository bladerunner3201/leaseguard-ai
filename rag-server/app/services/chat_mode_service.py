from dataclasses import dataclass

STRUCTURED_ANALYSIS = "structured_analysis"
EASY_EXPLANATION = "easy_explanation"
ANALOGY = "analogy"
LANDLORD_QUESTION = "landlord_question"
BRIEF_SUMMARY = "brief_summary"
REWRITE_CLAUSE = "rewrite_clause"
LEGAL_JUDGMENT_REFUSAL = "legal_judgment_refusal"

TOPIC_DEPOSIT_RETURN = "deposit_return"
TOPIC_SPECIAL_CLAUSE_REPAIR = "special_clause_repair"
TOPIC_MOVE_IN_FIXED_DATE = "move_in_fixed_date"
TOPIC_REGISTRY_CHECK = "registry_check"
TOPIC_JEONSE_FRAUD_PREVENTION = "jeonse_fraud_prevention"
TOPIC_GENERAL_CONTRACT_RISK = "general_contract_risk"

STYLE_STRUCTURED_ANALYSIS = STRUCTURED_ANALYSIS
STYLE_EASY_EXPLANATION = EASY_EXPLANATION
STYLE_ANALOGY = ANALOGY
STYLE_LANDLORD_QUESTION = LANDLORD_QUESTION
STYLE_BRIEF_SUMMARY = BRIEF_SUMMARY
STYLE_REWRITE_CLAUSE = REWRITE_CLAUSE

SAFETY_NORMAL = "normal"
SAFETY_LEGAL_JUDGMENT_SENSITIVE = "legal_judgment_sensitive"

LEGAL_JUDGMENT_MARKERS = [
    "무효",
    "위법",
    "불법",
    "소송",
    "이겨",
    "이길",
    "승소",
    "패소",
    "계약해도 돼",
    "계약해도 되",
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

LANDLORD_QUESTION_MARKERS = [
    "임대인에게",
    "집주인에게",
    "뭐라고 물어",
    "어떻게 말",
    "어떻게 요구",
    "어떻게 물어",
]

ANALOGY_MARKERS = ["비유", "예시", "예를 들어", "일상적으로 설명"]
EASY_EXPLANATION_MARKERS = ["쉽게", "너무 어려", "초보", "다시 설명", "풀어서 설명"]
BRIEF_SUMMARY_MARKERS = ["짧게", "핵심만", "요약", "세 줄", "3줄"]

FOLLOW_UP_MARKERS = [
    "그럼",
    "그 부분",
    "방금",
    "방금 말한",
    "그 조항",
    "이 부분",
    "그건",
    "그거",
    "앞에서 말한",
]

TOPIC_MARKERS = {
    TOPIC_DEPOSIT_RETURN: [
        "보증금",
        "반환",
        "돌려받",
        "임차권등기",
        "반환 지연",
        "deposit",
        "refund",
    ],
    TOPIC_SPECIAL_CLAUSE_REPAIR: [
        "특약",
        "불리",
        "수리비",
        "수선",
        "원상복구",
        "임차인 부담",
        "repair",
        "restoration",
    ],
    TOPIC_MOVE_IN_FIXED_DATE: [
        "전입신고",
        "확정일자",
        "대항력",
        "우선변제권",
        "move in",
        "fixed date",
    ],
    TOPIC_REGISTRY_CHECK: [
        "등기부",
        "근저당",
        "압류",
        "가압류",
        "선순위",
        "registry",
        "mortgage",
    ],
    TOPIC_JEONSE_FRAUD_PREVENTION: [
        "전세사기",
        "보증보험",
        "시세",
        "전세가율",
        "깡통전세",
        "jeonse fraud",
        "insurance",
    ],
}


@dataclass(frozen=True)
class ChatIntent:
    topic: str
    answerStyle: str
    safetyLevel: str
    isFollowUp: bool

    @property
    def response_mode(self) -> str:
        if self.safetyLevel == SAFETY_LEGAL_JUDGMENT_SENSITIVE:
            return LEGAL_JUDGMENT_REFUSAL
        return self.answerStyle


def detect_chat_intent(message: str) -> ChatIntent:
    normalized = (message or "").lower()
    return ChatIntent(
        topic=_detect_topic(normalized),
        answerStyle=_detect_answer_style(normalized),
        safetyLevel=_detect_safety_level(normalized),
        isFollowUp=detect_follow_up(message),
    )


def detect_response_mode(message: str) -> str:
    return detect_chat_intent(message).response_mode


def detect_follow_up(message: str) -> bool:
    normalized = message or ""
    return any(marker in normalized for marker in FOLLOW_UP_MARKERS)


def _detect_topic(normalized_message: str) -> str:
    for topic, markers in TOPIC_MARKERS.items():
        if any(marker in normalized_message for marker in markers):
            return topic
    return TOPIC_GENERAL_CONTRACT_RISK


def _detect_answer_style(normalized_message: str) -> str:
    if any(marker in normalized_message for marker in REWRITE_CLAUSE_MARKERS):
        return STYLE_REWRITE_CLAUSE
    if any(marker in normalized_message for marker in LANDLORD_QUESTION_MARKERS):
        return STYLE_LANDLORD_QUESTION
    if any(marker in normalized_message for marker in ANALOGY_MARKERS):
        return STYLE_ANALOGY
    if any(marker in normalized_message for marker in EASY_EXPLANATION_MARKERS):
        return STYLE_EASY_EXPLANATION
    if any(marker in normalized_message for marker in BRIEF_SUMMARY_MARKERS):
        return STYLE_BRIEF_SUMMARY
    return STYLE_STRUCTURED_ANALYSIS


def _detect_safety_level(normalized_message: str) -> str:
    if any(marker in normalized_message for marker in LEGAL_JUDGMENT_MARKERS):
        return SAFETY_LEGAL_JUDGMENT_SENSITIVE
    return SAFETY_NORMAL
