package com.leaseguard.contract.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDateTime;

@Entity
@Table(
        name = "contract_review_reports",
        uniqueConstraints = @UniqueConstraint(name = "uk_contract_review_reports_job_id", columnNames = "job_id")
)
public class ContractReviewReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "review_report_id")
    private Long reviewReportId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "contract_id", nullable = false)
    private Contract contract;

    @Column(name = "job_id", length = 100, nullable = false)
    private String jobId;

    @Column(name = "status", length = 30, nullable = false)
    private String status;

    @Column(name = "overall_risk_level", length = 30, nullable = false)
    private String overallRiskLevel;

    @Column(name = "summary", columnDefinition = "TEXT")
    private String summary;

    @Column(name = "report_markdown", columnDefinition = "LONGTEXT")
    private String reportMarkdown;

    @Column(name = "agent_results_json", columnDefinition = "LONGTEXT")
    private String agentResultsJson;

    @Column(name = "sources_json", columnDefinition = "LONGTEXT")
    private String sourcesJson;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    protected ContractReviewReport() {
    }

    public ContractReviewReport(
            Contract contract,
            String jobId,
            String status,
            String overallRiskLevel,
            String summary,
            String reportMarkdown,
            String agentResultsJson,
            String sourcesJson,
            LocalDateTime createdAt,
            LocalDateTime updatedAt
    ) {
        this.contract = contract;
        this.jobId = jobId;
        this.status = status;
        this.overallRiskLevel = overallRiskLevel;
        this.summary = summary;
        this.reportMarkdown = reportMarkdown;
        this.agentResultsJson = agentResultsJson;
        this.sourcesJson = sourcesJson;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getReviewReportId() {
        return reviewReportId;
    }

    public Contract getContract() {
        return contract;
    }

    public String getJobId() {
        return jobId;
    }

    public String getStatus() {
        return status;
    }

    public String getOverallRiskLevel() {
        return overallRiskLevel;
    }

    public String getSummary() {
        return summary;
    }

    public String getReportMarkdown() {
        return reportMarkdown;
    }

    public String getAgentResultsJson() {
        return agentResultsJson;
    }

    public String getSourcesJson() {
        return sourcesJson;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}
