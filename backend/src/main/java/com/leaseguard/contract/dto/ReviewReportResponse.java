package com.leaseguard.contract.dto;

import com.leaseguard.contract.entity.ContractReviewReport;
import com.leaseguard.rag.dto.ContractReviewJobStatusResponse;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public record ReviewReportResponse(
        Long reviewReportId,
        Long contractId,
        String jobId,
        String status,
        String overallRiskLevel,
        String summary,
        String reportMarkdown,
        Map<String, Object> agentResults,
        List<ContractReviewJobStatusResponse.ReviewSource> sources,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
    public static ReviewReportResponse of(
            ContractReviewReport report,
            Map<String, Object> agentResults,
            List<ContractReviewJobStatusResponse.ReviewSource> sources
    ) {
        return new ReviewReportResponse(
                report.getReviewReportId(),
                report.getContract().getContractId(),
                report.getJobId(),
                report.getStatus(),
                report.getOverallRiskLevel(),
                report.getSummary(),
                report.getReportMarkdown(),
                agentResults,
                sources,
                report.getCreatedAt(),
                report.getUpdatedAt()
        );
    }
}
