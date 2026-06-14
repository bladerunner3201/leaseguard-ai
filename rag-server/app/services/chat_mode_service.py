STRUCTURED_ANALYSIS = "structured_analysis"
EASY_EXPLANATION = "easy_explanation"
ANALOGY = "analogy"
LANDLORD_QUESTION = "landlord_question"
BRIEF_SUMMARY = "brief_summary"
REWRITE_CLAUSE = "rewrite_clause"
LEGAL_JUDGMENT_REFUSAL = "legal_judgment_refusal"

LEGAL_JUDGMENT_MARKERS = [
    "무효",
    "위법",
    "불법",
    "소송",
    "이겨",
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
