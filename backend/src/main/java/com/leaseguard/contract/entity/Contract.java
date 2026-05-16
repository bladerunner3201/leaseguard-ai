package com.leaseguard.contract.entity;

import com.leaseguard.anonymous.entity.AnonymousSession;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "contracts")
public class Contract {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "contract_id")
    private Long contractId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "anonymous_session_id", nullable = false)
    private AnonymousSession anonymousSession;

    @Column(name = "original_file_name", nullable = false)
    private String originalFileName;

    @Column(name = "stored_file_path", length = 500, nullable = false)
    private String storedFilePath;

    @Column(name = "status", length = 30, nullable = false)
    private String status;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    protected Contract() {
    }

    public Contract(
            AnonymousSession anonymousSession,
            String originalFileName,
            String storedFilePath,
            String status,
            LocalDateTime createdAt
    ) {
        this.anonymousSession = anonymousSession;
        this.originalFileName = originalFileName;
        this.storedFilePath = storedFilePath;
        this.status = status;
        this.createdAt = createdAt;
    }

    public Long getContractId() {
        return contractId;
    }

    public AnonymousSession getAnonymousSession() {
        return anonymousSession;
    }

    public String getOriginalFileName() {
        return originalFileName;
    }

    public String getStoredFilePath() {
        return storedFilePath;
    }

    public String getStatus() {
        return status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void updateStatus(String status) {
        this.status = status;
    }
}
