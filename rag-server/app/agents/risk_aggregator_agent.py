from app.schemas.review_schema import AggregatedRiskResult, SpecialistFinding, SpecialistReviewResult

RISK_ORDER = {"HIGH": 3, "CAUTION": 2, "LOW": 1}


def aggregate_risks(domain_results: list[SpecialistReviewResult]) -> AggregatedRiskResult:
    findings = _deduplicate_findings(
        finding
        for domain_result in domain_results
        for finding in domain_result.findings
    )
    findings.sort(key=lambda finding: RISK_ORDER.get(finding.riskLevel, 0), reverse=True)

    overall_risk_level = _overall_risk_level(findings)
    top_risks = findings[:3]

    return AggregatedRiskResult(
        overallRiskLevel=overall_risk_level,
        summary=_summary(overall_risk_level, top_risks),
        topRisks=top_risks,
        domainResults=domain_results,
    )


def _deduplicate_findings(findings) -> list[SpecialistFinding]:
    seen: set[tuple[str, str, str]] = set()
    unique_findings: list[SpecialistFinding] = []
    for finding in findings:
        key = (finding.category, finding.title, finding.contractEvidence[:120])
        if key in seen:
            continue
        seen.add(key)
        unique_findings.append(finding)
    return unique_findings


def _overall_risk_level(findings: list[SpecialistFinding]) -> str:
    if any(finding.riskLevel == "HIGH" for finding in findings):
        return "HIGH"
    if any(finding.riskLevel == "CAUTION" for finding in findings):
        return "CAUTION"
    return "LOW"


def _summary(overall_risk_level: str, top_risks: list[SpecialistFinding]) -> str:
    if not top_risks:
        return "No major review findings were generated from the current indexed contract chunks."
    risk_titles = ", ".join(finding.title for finding in top_risks)
    return f"Overall risk level is {overall_risk_level}. Key review items include: {risk_titles}."
