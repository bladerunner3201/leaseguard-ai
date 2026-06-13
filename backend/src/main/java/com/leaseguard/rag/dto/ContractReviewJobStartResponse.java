package com.leaseguard.rag.dto;

public record ContractReviewJobStartResponse(
        String jobId,
        String status,
        String message
) {
}
