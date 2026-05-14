package com.leaseguard.rag.dto;

public record ContractAnalyzeRequest(
        String anonymousSessionId,
        Long contractId,
        String filePath,
        String originalFileName
) {
}
