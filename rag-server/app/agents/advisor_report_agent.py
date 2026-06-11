import os

from openai import OpenAI

from app.schemas.review_schema import AggregatedRiskResult

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
REPORT_CAUTION_TEXT = "This report is not legal advice. It is a reference-based contract risk check."


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
        "You are LeaseGuard AI, a contract risk-check assistant for Korean real estate lease agreements. "
        "Write a user-friendly comprehensive review report based only on the provided aggregated findings. "
        "Do not make final legal judgments, do not decide whether the contract is valid or invalid, and do not predict litigation outcomes. "
        "Recommend expert consultation when final legal judgment is needed."
    )


def _user_prompt(aggregated_risk: AggregatedRiskResult, document_name: str | None) -> str:
    return (
        f"Document name: {document_name or 'unknown'}\n"
        f"Overall risk level: {aggregated_risk.overallRiskLevel}\n"
        f"Summary: {aggregated_risk.summary}\n\n"
        "Top risks:\n"
        + "\n".join(
            [
                (
                    f"- [{finding.riskLevel}] {finding.title}\n"
                    f"  Evidence: {finding.contractEvidence}\n"
                    f"  Reason: {finding.reason}\n"
                    f"  Recommendations: {', '.join(finding.recommendations)}"
                )
                for finding in aggregated_risk.topRisks
            ]
        )
        + "\n\n"
        "Write the report in Markdown with these sections:\n"
        "1. Overall Summary\n"
        "2. Top 3 Key Risks\n"
        "3. Domain Review Results\n"
        "4. Questions to Ask the Landlord\n"
        "5. Clauses or Wording That Need Confirmation\n"
        "6. Caution\n"
    )


def _template_report(aggregated_risk: AggregatedRiskResult, document_name: str | None) -> str:
    lines = [
        "# Multi-Agent Contract Review Report",
        "",
        "## 1. Overall Summary",
        f"Document: {document_name or 'unknown'}",
        f"Overall risk level: {aggregated_risk.overallRiskLevel}",
        aggregated_risk.summary,
        "",
        "## 2. Top 3 Key Risks",
    ]
    if aggregated_risk.topRisks:
        for index, finding in enumerate(aggregated_risk.topRisks, start=1):
            lines.extend(
                [
                    f"### {index}. {finding.title}",
                    f"- Risk level: {finding.riskLevel}",
                    f"- Contract evidence: {finding.contractEvidence}",
                    f"- Reason: {finding.reason}",
                    "- Recommended checks:",
                    *[f"  - {recommendation}" for recommendation in finding.recommendations],
                    "",
                ]
            )
    else:
        lines.append("No top risk items were identified from the current indexed contract chunks.")

    lines.extend(["## 3. Domain Review Results"])
    for domain_result in aggregated_risk.domainResults:
        lines.append(f"### {domain_result.domain}")
        for finding in domain_result.findings:
            lines.extend(
                [
                    f"- Risk level: {finding.riskLevel}",
                    f"- Finding: {finding.title}",
                    f"- Evidence: {finding.contractEvidence}",
                    f"- Reason: {finding.reason}",
                    "",
                ]
            )

    lines.extend(
        [
            "## 4. Questions to Ask the Landlord",
            "- Please confirm whether the deposit return date is tied to the lease end date or another condition.",
            "- Please clarify which repair costs are tenant responsibility and which are landlord responsibility.",
            "- Please confirm whether any special clause changes standard responsibility allocation.",
            "",
            "## 5. Clauses or Wording That Need Confirmation",
            "Review broad expressions about deposit return, repair cost, restoration, special clauses, move-in registration, registry records, and guarantee insurance.",
            "",
            "## 6. Caution",
            REPORT_CAUTION_TEXT,
        ]
    )
    return "\n".join(lines)


def _ensure_caution(report: str) -> str:
    if REPORT_CAUTION_TEXT in report:
        return report
    return f"{report}\n\n## Caution\n{REPORT_CAUTION_TEXT}"
