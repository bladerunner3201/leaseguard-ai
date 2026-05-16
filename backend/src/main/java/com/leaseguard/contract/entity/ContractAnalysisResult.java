package com.leaseguard.contract.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "contract_analysis_results")
public class ContractAnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "analysis_id")
    private Long analysisId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "contract_id", nullable = false)
    private Contract contract;

    @Column(name = "overall_risk_level", length = 30, nullable = false)
    private String overallRiskLevel;

    @Column(name = "summary", columnDefinition = "TEXT")
    private String summary;

    @Column(name = "risk_items_json", columnDefinition = "JSON")
    private String riskItemsJson;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    protected ContractAnalysisResult() {
    }

    public ContractAnalysisResult(
            Contract contract,
            String overallRiskLevel,
            String summary,
            String riskItemsJson,
            LocalDateTime createdAt
    ) {
        this.contract = contract;
        this.overallRiskLevel = overallRiskLevel;
        this.summary = summary;
        this.riskItemsJson = riskItemsJson;
        this.createdAt = createdAt;
    }

    public Long getAnalysisId() {
        return analysisId;
    }

    public Contract getContract() {
        return contract;
    }

    public String getOverallRiskLevel() {
        return overallRiskLevel;
    }

    public String getSummary() {
        return summary;
    }

    public String getRiskItemsJson() {
        return riskItemsJson;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
