package com.leaseguard.contract.repository;

import com.leaseguard.contract.entity.Contract;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ContractRepository extends JpaRepository<Contract, Long> {

    List<Contract> findByAnonymousSessionAnonymousSessionIdAndStatusNotOrderByCreatedAtDesc(
            String anonymousSessionId,
            String status
    );

    Optional<Contract> findByContractIdAndAnonymousSessionAnonymousSessionId(
            Long contractId,
            String anonymousSessionId
    );
}
