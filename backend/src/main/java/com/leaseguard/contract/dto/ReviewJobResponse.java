package com.leaseguard.contract.dto;

import com.leaseguard.rag.dto.ContractReviewJobStatusResponse;

public record ReviewJobResponse(
        String jobId,
        String status,
        Integer progress,
        ContractReviewJobStatusResponse.ContractReviewResult result,
        ReviewReportResponse savedReviewReport,
        String error
) {
    public static ReviewJobResponse of(
            ContractReviewJobStatusResponse jobStatus,
            ReviewReportResponse savedReviewReport
    ) {
        return new ReviewJobResponse(
                jobStatus.jobId(),
                jobStatus.status(),
                jobStatus.progress(),
                jobStatus.result(),
                savedReviewReport,
                jobStatus.error()
        );
    }

    public static ReviewJobResponse failedWithSavedReport(
            String jobId,
            String error,
            ReviewReportResponse savedReviewReport
    ) {
        return new ReviewJobResponse(jobId, "FAILED", 0, null, savedReviewReport, error);
    }
}
