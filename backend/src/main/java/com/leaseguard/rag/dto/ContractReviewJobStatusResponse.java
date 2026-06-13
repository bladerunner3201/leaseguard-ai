package com.leaseguard.rag.dto;

import java.util.List;
import java.util.Map;

public record ContractReviewJobStatusResponse(
        String jobId,
        String status,
        Integer progress,
        ContractReviewResult result,
        String error
) {
    public record ContractReviewResult(
            String overallRiskLevel,
            String summary,
            Map<String, Object> agentResults,
            String reportMarkdown,
            List<ReviewSource> sources
    ) {
    }

    public record ReviewSource(
            String sourceType,
            String sourceTitle,
            String chunkText,
            Double similarityScore
    ) {
    }
}
