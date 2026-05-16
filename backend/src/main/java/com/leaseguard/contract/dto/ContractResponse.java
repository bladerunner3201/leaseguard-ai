package com.leaseguard.contract.dto;

import com.leaseguard.contract.entity.Contract;
import java.time.LocalDateTime;

public record ContractResponse(
        Long contractId,
        String originalFileName,
        String status,
        LocalDateTime createdAt
) {
    public static ContractResponse from(Contract contract) {
        return new ContractResponse(
                contract.getContractId(),
                contract.getOriginalFileName(),
                contract.getStatus(),
                contract.getCreatedAt()
        );
    }
}
