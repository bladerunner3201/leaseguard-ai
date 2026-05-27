import os

from openai import OpenAI

from app.schemas.chat_schema import RagSource

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """
당신은 LeaseGuard AI입니다.
LeaseGuard AI는 부동산 임대차계약서를 처음 읽는 사용자를 위한 계약 위험 점검 보조 챗봇입니다.
사용자는 법률 비전문가라고 가정하고, 어려운 법률 용어는 쉬운 말로 풀어서 설명하세요.

당신은 변호사, 공인중개사, 법률 전문가가 아니며 최종 법률 판단을 단정하지 않습니다.
계약이 무효인지, 위법인지, 소송에서 이길 수 있는지, 계약해도 되는지 단정하지 마세요.
사용자가 "이 계약 무효야?", "소송하면 이겨?", "무조건 위법이야?"처럼 법률 판단을 요구하면
제공된 자료만으로는 단정할 수 없다고 말하고 변호사 또는 공인중개사 같은 전문가 상담을 권장하세요.

반드시 제공된 계약서 조각과 reference source를 근거로만 답변하세요.
sources에 없는 내용은 추측하지 말고 "제공된 자료만으로는 확인하기 어렵습니다"라고 답하세요.
검색된 source의 내용을 바탕으로 위험 가능성과 확인사항을 친절하고 쉽게 설명하세요.

답변은 반드시 한국어로 작성하고, 아래 형식을 유지하세요.
1. 요약 판단
2. 계약서에서 확인된 내용
3. 관련 근거
4. 위험 또는 확인 필요 사항
5. 다음 행동
6. 주의 문구

마지막 "주의 문구"에는 반드시 다음 문장을 포함하세요.
"본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."
""".strip()


def generate_answer(message: str, sources: list[RagSource]) -> str:
    if not sources:
        return _fallback_answer_without_sources()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return generate_template_answer(message, sources)

    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_prompt(message, sources),
                },
            ],
            temperature=0.2,
        )
        answer = completion.choices[0].message.content
        if not answer:
            return generate_template_answer(message, sources)
        return answer.strip()
    except Exception as exception:
        return (
            generate_template_answer(message, sources)
            + "\n\n[OpenAI fallback] "
            + f"OpenAI answer generation failed: {type(exception).__name__}"
        )


def generate_template_answer(message: str, sources: list[RagSource]) -> str:
    contract_count = sum(1 for source in sources if source.sourceType == "contract")
    reference_count = len(sources) - contract_count

    return (
        "1. 요약 판단\n"
        "검색된 자료를 보면 확인이 필요한 부분이 있을 수 있습니다. "
        "다만 OpenAI 호출을 사용하지 못해 임시 template 답변을 반환합니다.\n\n"
        "2. 계약서에서 확인된 내용\n"
        f"검색된 계약서 조각은 {contract_count}개입니다. 사용자 질문은 다음과 같습니다: {message}\n\n"
        "3. 관련 근거\n"
        f"검색된 reference source는 {reference_count}개입니다. 화면의 sources 목록에서 근거 문장을 확인하세요.\n\n"
        "4. 위험 또는 확인 필요 사항\n"
        "검색 결과만으로 최종 법률 판단은 할 수 없습니다. 보증금 반환 조건, 특약, 등기부등본, "
        "전입신고와 확정일자 등 관련 자료를 함께 확인해야 합니다. "
        "제공된 자료만으로는 확인하기 어렵습니다.\n\n"
        "5. 다음 행동\n"
        "위 sources의 계약서 조각과 reference 문서를 비교하고, 부족한 서류나 불명확한 표현이 있으면 "
        "임대인에게 확인하거나 전문가 상담을 고려하세요.\n\n"
        "6. 주의 문구\n"
        "본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."
    )


def _fallback_answer_without_sources() -> str:
    return (
        "1. 요약 판단\n"
        "검색된 근거 source가 없어 답변을 생성하기 어렵습니다.\n\n"
        "2. 계약서에서 확인된 내용\n"
        "제공된 검색 결과가 없습니다.\n\n"
        "3. 관련 근거\n"
        "관련 계약서 조각 또는 reference source가 검색되지 않았습니다.\n\n"
        "4. 위험 또는 확인 필요 사항\n"
        "제공된 자료만으로는 확인하기 어렵습니다. 계약서와 reference 문서 인덱싱 상태를 먼저 확인해야 합니다.\n\n"
        "5. 다음 행동\n"
        "/rag/references/index를 실행하고 계약서를 다시 인덱싱한 뒤 질문하세요.\n\n"
        "6. 주의 문구\n"
        "본 답변은 법률 자문이 아니라 참고용 위험 점검입니다."
    )


def _build_user_prompt(message: str, sources: list[RagSource]) -> str:
    return (
        f"사용자 질문:\n{message}\n\n"
        "검색된 sources:\n"
        f"{_format_sources_for_prompt(sources)}\n\n"
        "위 sources를 근거로만 답변하세요. "
        "sources에서 확인할 수 없는 내용은 반드시 '제공된 자료만으로는 확인하기 어렵습니다'라고 말하세요."
    )


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
