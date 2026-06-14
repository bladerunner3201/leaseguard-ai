package com.leaseguard.contract.controller;

import com.leaseguard.contract.dto.ContractAnalysisResponse;
import com.leaseguard.contract.dto.ContractResponse;
import com.leaseguard.contract.dto.ContractUploadResponse;
import com.leaseguard.contract.dto.ReviewJobResponse;
import com.leaseguard.contract.dto.ReviewReportResponse;
import com.leaseguard.contract.service.ContractService;
import com.leaseguard.global.response.ApiResponse;
import com.leaseguard.rag.dto.ContractReviewJobStartResponse;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/contracts")
public class ContractController {

    private static final String SESSION_HEADER = "X-Anonymous-Session-Id";

    private final ContractService contractService;

    public ContractController(ContractService contractService) {
        this.contractService = contractService;
    }

    @PostMapping
    public ApiResponse<ContractUploadResponse> uploadContract(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @RequestParam("file") MultipartFile file
    ) {
        return ApiResponse.ok(contractService.uploadContract(anonymousSessionId, file));
    }

    @GetMapping
    public ApiResponse<List<ContractResponse>> getContracts(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId
    ) {
        return ApiResponse.ok(contractService.getContracts(anonymousSessionId));
    }

    @GetMapping("/{contractId}")
    public ApiResponse<ContractResponse> getContract(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId
    ) {
        return ApiResponse.ok(contractService.getContract(anonymousSessionId, contractId));
    }

    @GetMapping("/{contractId}/analysis")
    public ApiResponse<ContractAnalysisResponse> getAnalysis(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId
    ) {
        return ApiResponse.ok(contractService.getAnalysis(anonymousSessionId, contractId));
    }

    @DeleteMapping("/{contractId}")
    public ApiResponse<Void> deleteContract(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId
    ) {
        contractService.deleteContract(anonymousSessionId, contractId);
        return ApiResponse.ok(null);
    }

    @PostMapping("/{contractId}/review-jobs")
    public ApiResponse<ContractReviewJobStartResponse> startReviewJob(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId
    ) {
        return ApiResponse.ok(contractService.startReviewJob(anonymousSessionId, contractId));
    }

    @GetMapping("/{contractId}/review-jobs/{jobId}")
    public ApiResponse<ReviewJobResponse> getReviewJob(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId,
            @PathVariable String jobId
    ) {
        return ApiResponse.ok(contractService.getReviewJob(anonymousSessionId, contractId, jobId));
    }

    @GetMapping("/{contractId}/review-report")
    public ApiResponse<ReviewReportResponse> getLatestReviewReport(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long contractId
    ) {
        return ApiResponse.ok(contractService.getLatestReviewReport(anonymousSessionId, contractId));
    }
}
