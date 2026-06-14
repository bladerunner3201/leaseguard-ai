package com.leaseguard.contract.repository;

import com.leaseguard.contract.entity.ContractReviewReport;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ContractReviewReportRepository extends JpaRepository<ContractReviewReport, Long> {

    Optional<ContractReviewReport> findFirstByContractContractIdOrderByUpdatedAtDesc(Long contractId);

    Optional<ContractReviewReport> findByJobId(String jobId);

    Optional<ContractReviewReport> findByContractContractIdAndJobId(Long contractId, String jobId);
}
