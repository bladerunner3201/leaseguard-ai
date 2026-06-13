package com.leaseguard.rag.dto;

public record ContractReviewRequest(
        String anonymousSessionId,
        Long contractId,
        String documentName
) {
}
