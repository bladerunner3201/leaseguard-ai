import os

from openai import OpenAI

from app.schemas.review_schema import AggregatedRiskResult

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
REPORT_CAUTION_TEXT = "본 리포트는 법률 자문이 아니라 참고용 위험 점검입니다."


def build_report(aggregated_risk: AggregatedRiskResult, document_name: str | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _template_report(aggregated_risk, document_name)

    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(aggregated_risk, document_name)},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content
        if not content:
            return _template_report(aggregated_risk, document_name)
        return _ensure_caution(content.strip())
    except Exception as exception:
        print(f"[multi-agent-review] OpenAI report generation failed: {type(exception).__name__}: {exception}")
        return _template_report(aggregated_risk, document_name)


def _system_prompt() -> str:
    return (
        "당신은 LeaseGuard AI의 Advisor & Report Agent입니다. "
        "한국 부동산 임대차계약서를 처음 읽는 사용자도 이해할 수 있도록 종합 검토 리포트를 작성합니다. "
        "반드시 한국어로만 답변하고, 제목과 본문도 모두 한국어로 작성하세요. "
        "제공된 agent findings와 근거 안에서만 설명하고, 확인되지 않은 사실을 단정하지 마세요. "
        "계약 무효 여부, 위법 여부, 소송 승패, 계약 체결 가능 여부 같은 최종 법률 판단을 단정하지 마세요. "
        "최종 판단이 필요한 부분은 전문가 상담을 권장하세요."
    )


def _user_prompt(aggregated_risk: AggregatedRiskResult, document_name: str | None) -> str:
    return (
        f"문서명: {document_name or '알 수 없음'}\n"
        f"종합 위험도: {aggregated_risk.overallRiskLevel}\n"
        f"요약: {aggregated_risk.summary}\n\n"
        "주요 위험 항목:\n"
        + "\n".join(
            [
                (
                    f"- [{finding.riskLevel}] {finding.title}\n"
                    f"  계약서 근거: {finding.contractEvidence}\n"
                    f"  검토 이유: {finding.reason}\n"
                    f"  확인 권장 사항: {', '.join(finding.recommendations)}"
                )
                for finding in aggregated_risk.topRisks
            ]
        )
        + "\n\n"
        "아래 한국어 Markdown 섹션으로 리포트를 작성하세요.\n"
        "영어 heading을 사용하지 마세요.\n"
        "1. 종합 요약\n"
        "2. 핵심 위험 3가지\n"
        "3. 영역별 검토 결과\n"
        "4. 임대인 또는 공인중개사에게 확인할 질문\n"
        "5. 확인이 필요한 조항 또는 문구\n"
        "6. 주의 문구\n"
        f"마지막 주의 문구에는 반드시 '{REPORT_CAUTION_TEXT}'를 포함하세요.\n"
    )


def _template_report(aggregated_risk: AggregatedRiskResult, document_name: str | None) -> str:
    lines = [
        "# 멀티에이전트 계약서 종합 검토 리포트",
        "",
        "## 1. 종합 요약",
        f"- 문서명: {document_name or '알 수 없음'}",
        f"- 종합 위험도: {aggregated_risk.overallRiskLevel}",
        f"- 요약: {aggregated_risk.summary}",
        "",
        "## 2. 핵심 위험 3가지",
    ]
    if aggregated_risk.topRisks:
        for index, finding in enumerate(aggregated_risk.topRisks, start=1):
            lines.extend(
                [
                    f"### {index}. {finding.title}",
                    f"- 위험도: {finding.riskLevel}",
                    f"- 계약서 근거: {finding.contractEvidence}",
                    f"- 확인 이유: {finding.reason}",
                    "- 확인 권장 사항:",
                    *[f"  - {recommendation}" for recommendation in finding.recommendations],
                    "",
                ]
            )
    else:
        lines.append("현재 인덱싱된 계약서 조각에서는 주요 위험 항목이 뚜렷하게 확인되지 않았습니다.")

    lines.extend(["", "## 3. 영역별 검토 결과"])
    for domain_result in aggregated_risk.domainResults:
        lines.append(f"### {_domain_label(domain_result.domain)}")
        for finding in domain_result.findings:
            lines.extend(
                [
                    f"- 위험도: {finding.riskLevel}",
                    f"- 검토 항목: {finding.title}",
                    f"- 계약서 근거: {finding.contractEvidence}",
                    f"- 확인 이유: {finding.reason}",
                    "",
                ]
            )

    lines.extend(
        [
            "## 4. 임대인 또는 공인중개사에게 확인할 질문",
            "- 보증금 반환 시점이 계약 종료일 기준인지, 다른 조건이 붙어 있는지 확인해 주세요.",
            "- 수리비와 원상복구 책임이 임차인 부담인지 임대인 부담인지 항목별로 확인해 주세요.",
            "- 특약 조항이 표준적인 책임 범위를 바꾸는지 서면으로 명확히 확인해 주세요.",
            "",
            "## 5. 확인이 필요한 조항 또는 문구",
            "보증금 반환, 수리비, 원상복구, 특약, 전입신고와 확정일자, 등기부등본, 보증보험 관련 문구는 계약 전 다시 확인하는 것이 좋습니다.",
            "",
            "## 6. 주의 문구",
            REPORT_CAUTION_TEXT,
        ]
    )
    return "\n".join(lines)


def _domain_label(domain: str) -> str:
    labels = {
        "deposit_return": "보증금 반환",
        "special_clause": "특약 조항",
        "repair_cost": "수리비와 원상복구",
        "move_in_fixed_date": "전입신고와 확정일자",
        "registry_check": "등기부등본 확인",
        "jeonse_fraud_prevention": "전세사기 예방",
        "standard_contract": "표준계약서 항목",
    }
    return labels.get(domain, domain)


def _ensure_caution(report: str) -> str:
    if REPORT_CAUTION_TEXT in report:
        return report
    return f"{report}\n\n## 주의 문구\n{REPORT_CAUTION_TEXT}"
