package com.leaseguard.contract.dto;

import com.leaseguard.contract.entity.ContractAnalysisResult;
import com.leaseguard.rag.dto.ContractAnalyzeResponse;
import java.time.LocalDateTime;
import java.util.List;

public record ContractAnalysisResponse(
        Long analysisId,
        Long contractId,
        String overallRiskLevel,
        String summary,
        List<ContractAnalyzeResponse.RiskItem> riskItems,
        LocalDateTime createdAt
) {
    public static ContractAnalysisResponse of(
            ContractAnalysisResult analysisResult,
            List<ContractAnalyzeResponse.RiskItem> riskItems
    ) {
        return new ContractAnalysisResponse(
                analysisResult.getAnalysisId(),
                analysisResult.getContract().getContractId(),
                analysisResult.getOverallRiskLevel(),
                analysisResult.getSummary(),
                riskItems,
                analysisResult.getCreatedAt()
        );
    }
}
