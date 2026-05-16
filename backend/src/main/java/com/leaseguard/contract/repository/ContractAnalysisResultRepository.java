package com.leaseguard.contract.repository;

import com.leaseguard.contract.entity.ContractAnalysisResult;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ContractAnalysisResultRepository extends JpaRepository<ContractAnalysisResult, Long> {

    Optional<ContractAnalysisResult> findByContractContractId(Long contractId);
}
