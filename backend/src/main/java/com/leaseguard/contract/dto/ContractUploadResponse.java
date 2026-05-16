package com.leaseguard.contract.dto;

public record ContractUploadResponse(
        ContractResponse contract,
        ContractAnalysisResponse analysis
) {
}
