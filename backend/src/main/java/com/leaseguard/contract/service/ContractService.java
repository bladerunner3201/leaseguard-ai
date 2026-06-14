package com.leaseguard.contract.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.leaseguard.anonymous.entity.AnonymousSession;
import com.leaseguard.anonymous.repository.AnonymousSessionRepository;
import com.leaseguard.contract.dto.ContractAnalysisResponse;
import com.leaseguard.contract.dto.ContractResponse;
import com.leaseguard.contract.dto.ContractUploadResponse;
import com.leaseguard.contract.dto.ReviewJobResponse;
import com.leaseguard.contract.dto.ReviewReportResponse;
import com.leaseguard.contract.entity.Contract;
import com.leaseguard.contract.entity.ContractAnalysisResult;
import com.leaseguard.contract.entity.ContractReviewReport;
import com.leaseguard.contract.repository.ContractAnalysisResultRepository;
import com.leaseguard.contract.repository.ContractRepository;
import com.leaseguard.contract.repository.ContractReviewReportRepository;
import com.leaseguard.global.exception.BadRequestException;
import com.leaseguard.global.exception.ForbiddenException;
import com.leaseguard.global.exception.NotFoundException;
import com.leaseguard.rag.client.RagServerClient;
import com.leaseguard.rag.dto.ContractAnalyzeRequest;
import com.leaseguard.rag.dto.ContractAnalyzeResponse;
import com.leaseguard.rag.dto.ContractReviewJobStartResponse;
import com.leaseguard.rag.dto.ContractReviewJobStatusResponse;
import com.leaseguard.rag.dto.ContractReviewRequest;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.multipart.MultipartFile;

@Service
public class ContractService {

    private final AnonymousSessionRepository anonymousSessionRepository;
    private final ContractRepository contractRepository;
    private final ContractAnalysisResultRepository analysisResultRepository;
    private final ContractReviewReportRepository reviewReportRepository;
    private final RagServerClient ragServerClient;
    private final ObjectMapper objectMapper;
    private final Path uploadRoot;

    public ContractService(
            AnonymousSessionRepository anonymousSessionRepository,
            ContractRepository contractRepository,
            ContractAnalysisResultRepository analysisResultRepository,
            ContractReviewReportRepository reviewReportRepository,
            RagServerClient ragServerClient,
            ObjectMapper objectMapper,
            @Value("${file.upload-root:uploads}") String uploadRoot
    ) {
        this.anonymousSessionRepository = anonymousSessionRepository;
        this.contractRepository = contractRepository;
        this.analysisResultRepository = analysisResultRepository;
        this.reviewReportRepository = reviewReportRepository;
        this.ragServerClient = ragServerClient;
        this.objectMapper = objectMapper;
        this.uploadRoot = Path.of(uploadRoot).toAbsolutePath().normalize();
    }

    @Transactional
    public ContractUploadResponse uploadContract(String anonymousSessionId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("업로드할 계약서 파일이 필요합니다.");
        }

        validateSupportedFileExtension(file);
        AnonymousSession anonymousSession = findAnonymousSession(anonymousSessionId);
        Path storedFilePath = storeFile(anonymousSessionId, file);
        String originalFilename = normalizeOriginalFilename(file);

        Contract contract = contractRepository.save(new Contract(
                anonymousSession,
                originalFilename,
                storedFilePath.toString(),
                "UPLOADED",
                LocalDateTime.now()
        ));

        ContractAnalyzeResponse ragResponse;
        try {
            ragResponse = ragServerClient.indexContract(new ContractAnalyzeRequest(
                    anonymousSessionId,
                    contract.getContractId(),
                    contract.getStoredFilePath(),
                    contract.getOriginalFileName()
            ));
        } catch (RestClientResponseException exception) {
            if (exception.getStatusCode().is4xxClientError()) {
                throw new BadRequestException(exception.getResponseBodyAsString());
            }
            throw exception;
        }

        ContractAnalyzeResponse.Analysis analysis = ragResponse.analysis();
        ContractAnalysisResult analysisResult = analysisResultRepository.save(new ContractAnalysisResult(
                contract,
                analysis.overallRiskLevel(),
                analysis.summary(),
                writeRiskItems(analysis.riskItems()),
                LocalDateTime.now()
        ));

        contract.updateStatus(ragResponse.status());
        return new ContractUploadResponse(
                ContractResponse.from(contract),
                ContractAnalysisResponse.of(analysisResult, analysis.riskItems())
        );
    }

    @Transactional(readOnly = true)
    public List<ContractResponse> getContracts(String anonymousSessionId) {
        ensureAnonymousSessionExists(anonymousSessionId);
        return contractRepository.findByAnonymousSessionAnonymousSessionIdAndStatusNotOrderByCreatedAtDesc(
                        anonymousSessionId,
                        "DELETED"
                )
                .stream()
                .map(ContractResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public ContractResponse getContract(String anonymousSessionId, Long contractId) {
        return ContractResponse.from(findOwnedContract(anonymousSessionId, contractId));
    }

    @Transactional(readOnly = true)
    public ContractAnalysisResponse getAnalysis(String anonymousSessionId, Long contractId) {
        Contract contract = findOwnedContract(anonymousSessionId, contractId);
        ContractAnalysisResult analysisResult = analysisResultRepository.findByContractContractId(contract.getContractId())
                .orElseThrow(() -> new NotFoundException("계약서 분석 결과를 찾을 수 없습니다."));
        return ContractAnalysisResponse.of(analysisResult, readRiskItems(analysisResult.getRiskItemsJson()));
    }

    @Transactional
    public void deleteContract(String anonymousSessionId, Long contractId) {
        Contract contract = findOwnedContract(anonymousSessionId, contractId);
        contract.updateStatus("DELETED");
    }

    @Transactional(readOnly = true)
    public ContractReviewJobStartResponse startReviewJob(String anonymousSessionId, Long contractId) {
        Contract contract = findOwnedContract(anonymousSessionId, contractId);
        return ragServerClient.startReviewJob(new ContractReviewRequest(
                anonymousSessionId,
                contract.getContractId(),
                contract.getOriginalFileName()
        ));
    }

    @Transactional
    public ReviewJobResponse getReviewJob(String anonymousSessionId, Long contractId, String jobId) {
        Contract contract = findOwnedContract(anonymousSessionId, contractId);
        ReviewReportResponse alreadySaved = findSavedReviewReportByJobId(contract.getContractId(), jobId);
        if (alreadySaved != null) {
            return new ReviewJobResponse(jobId, "COMPLETED", 100, null, alreadySaved, null);
        }

        ContractReviewJobStatusResponse jobStatus;
        try {
            jobStatus = ragServerClient.getReviewJob(jobId);
        } catch (RestClientResponseException exception) {
            ReviewReportResponse latestReport = findLatestReviewReportOrNull(contract.getContractId());
            String message = "진행 중이던 리포트 생성 작업을 찾을 수 없습니다. 필요하면 다시 생성해 주세요.";
            if (latestReport != null) {
                return ReviewJobResponse.failedWithSavedReport(jobId, message, latestReport);
            }
            throw new NotFoundException(message);
        }

        ReviewReportResponse savedReviewReport = null;
        if ("COMPLETED".equals(jobStatus.status()) && jobStatus.result() != null) {
            savedReviewReport = saveCompletedReviewReport(contract, jobStatus);
        }
        return ReviewJobResponse.of(jobStatus, savedReviewReport);
    }

    @Transactional(readOnly = true)
    public ReviewReportResponse getLatestReviewReport(String anonymousSessionId, Long contractId) {
        Contract contract = findOwnedContract(anonymousSessionId, contractId);
        return reviewReportRepository.findFirstByContractContractIdOrderByUpdatedAtDesc(contract.getContractId())
                .map(this::toReviewReportResponse)
                .orElseThrow(() -> new NotFoundException("저장된 멀티에이전트 리포트가 없습니다."));
    }

    @Transactional(readOnly = true)
    public Contract findOwnedContract(String anonymousSessionId, Long contractId) {
        Contract contract = contractRepository.findById(contractId)
                .orElseThrow(() -> new NotFoundException("계약서를 찾을 수 없습니다."));
        if (!contract.getAnonymousSession().getAnonymousSessionId().equals(anonymousSessionId)) {
            throw new ForbiddenException("다른 익명 세션의 계약서에는 접근할 수 없습니다.");
        }
        if ("DELETED".equals(contract.getStatus())) {
            throw new NotFoundException("삭제된 계약서입니다.");
        }
        return contract;
    }

    private AnonymousSession findAnonymousSession(String anonymousSessionId) {
        return anonymousSessionRepository.findById(anonymousSessionId)
                .orElseThrow(() -> new NotFoundException("익명 세션을 찾을 수 없습니다."));
    }

    private void ensureAnonymousSessionExists(String anonymousSessionId) {
        if (!anonymousSessionRepository.existsById(anonymousSessionId)) {
            throw new NotFoundException("익명 세션을 찾을 수 없습니다.");
        }
    }

    private Path storeFile(String anonymousSessionId, MultipartFile file) {
        String originalFilename = normalizeOriginalFilename(file);
        String sanitizedFilename = originalFilename.replaceAll("[\\\\/:*?\"<>|]", "_");
        Path directory = uploadRoot.resolve("contracts").resolve(anonymousSessionId).normalize();
        Path storedFilePath = directory.resolve(UUID.randomUUID() + "_" + sanitizedFilename).normalize();

        if (!storedFilePath.startsWith(uploadRoot)) {
            throw new IllegalArgumentException("잘못된 파일 경로입니다.");
        }

        try {
            Files.createDirectories(directory);
            file.transferTo(storedFilePath);
            return storedFilePath;
        } catch (IOException exception) {
            throw new IllegalStateException("계약서 파일 저장에 실패했습니다.", exception);
        }
    }

    private String normalizeOriginalFilename(MultipartFile file) {
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isBlank()) {
            return "contract";
        }
        return originalFilename;
    }

    private void validateSupportedFileExtension(MultipartFile file) {
        String originalFilename = normalizeOriginalFilename(file);
        String lowerFilename = originalFilename.toLowerCase(Locale.ROOT);
        if (!lowerFilename.endsWith(".txt") && !lowerFilename.endsWith(".pdf")) {
            throw new BadRequestException("Only .txt and .pdf contract files are supported.");
        }
    }

    private String writeRiskItems(List<ContractAnalyzeResponse.RiskItem> riskItems) {
        try {
            return objectMapper.writeValueAsString(riskItems == null ? List.of() : riskItems);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("위험 항목 직렬화에 실패했습니다.", exception);
        }
    }

    private List<ContractAnalyzeResponse.RiskItem> readRiskItems(String riskItemsJson) {
        try {
            return objectMapper.readValue(riskItemsJson, new TypeReference<>() {
            });
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("위험 항목 역직렬화에 실패했습니다.", exception);
        }
    }

    private ReviewReportResponse saveCompletedReviewReport(
            Contract contract,
            ContractReviewJobStatusResponse jobStatus
    ) {
        return reviewReportRepository.findByContractContractIdAndJobId(contract.getContractId(), jobStatus.jobId())
                .map(this::toReviewReportResponse)
                .orElseGet(() -> {
                    ContractReviewJobStatusResponse.ContractReviewResult result = jobStatus.result();
                    LocalDateTime now = LocalDateTime.now();
                    ContractReviewReport report = reviewReportRepository.save(new ContractReviewReport(
                            contract,
                            jobStatus.jobId(),
                            jobStatus.status(),
                            result.overallRiskLevel(),
                            result.summary(),
                            result.reportMarkdown(),
                            writeJson(result.agentResults()),
                            writeJson(result.sources()),
                            now,
                            now
                    ));
                    return toReviewReportResponse(report);
                });
    }

    private ReviewReportResponse findSavedReviewReportByJobId(Long contractId, String jobId) {
        return reviewReportRepository.findByContractContractIdAndJobId(contractId, jobId)
                .map(this::toReviewReportResponse)
                .orElse(null);
    }

    private ReviewReportResponse findLatestReviewReportOrNull(Long contractId) {
        return reviewReportRepository.findFirstByContractContractIdOrderByUpdatedAtDesc(contractId)
                .map(this::toReviewReportResponse)
                .orElse(null);
    }

    private ReviewReportResponse toReviewReportResponse(ContractReviewReport report) {
        return ReviewReportResponse.of(
                report,
                readAgentResults(report.getAgentResultsJson()),
                readSources(report.getSourcesJson())
        );
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("멀티에이전트 리포트 JSON 저장에 실패했습니다.", exception);
        }
    }

    private Map<String, Object> readAgentResults(String agentResultsJson) {
        if (agentResultsJson == null || agentResultsJson.isBlank() || "null".equals(agentResultsJson)) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(agentResultsJson, new TypeReference<>() {
            });
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("멀티에이전트 agentResults JSON 복원에 실패했습니다.", exception);
        }
    }

    private List<ContractReviewJobStatusResponse.ReviewSource> readSources(String sourcesJson) {
        if (sourcesJson == null || sourcesJson.isBlank() || "null".equals(sourcesJson)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(sourcesJson, new TypeReference<>() {
            });
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("멀티에이전트 sources JSON 복원에 실패했습니다.", exception);
        }
    }
}
