package com.leaseguard.rag.dto;

import java.util.List;

public record ContractAnalyzeResponse(
        Long contractId,
        String status,
        Analysis analysis
) {
    public record Analysis(
            String overallRiskLevel,
            String summary,
            List<RiskItem> riskItems
    ) {
    }

    public record RiskItem(
            String category,
            String riskLevel,
            String title,
            String description,
            String evidence
    ) {
    }
}
