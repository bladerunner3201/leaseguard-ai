package com.leaseguard.chat.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.leaseguard.anonymous.entity.AnonymousSession;
import com.leaseguard.anonymous.repository.AnonymousSessionRepository;
import com.leaseguard.chat.dto.ChatAnswerResponse;
import com.leaseguard.chat.dto.ChatMessageCreateRequest;
import com.leaseguard.chat.dto.ChatMessageResponse;
import com.leaseguard.chat.dto.ChatSessionCreateRequest;
import com.leaseguard.chat.dto.ChatSessionResponse;
import com.leaseguard.chat.dto.MessageSourceResponse;
import com.leaseguard.chat.entity.ChatMessage;
import com.leaseguard.chat.entity.ChatSession;
import com.leaseguard.chat.entity.MessageSource;
import com.leaseguard.chat.repository.ChatMessageRepository;
import com.leaseguard.chat.repository.ChatSessionRepository;
import com.leaseguard.chat.repository.MessageSourceRepository;
import com.leaseguard.contract.entity.Contract;
import com.leaseguard.contract.service.ContractService;
import com.leaseguard.global.exception.BadRequestException;
import com.leaseguard.global.exception.ForbiddenException;
import com.leaseguard.global.exception.NotFoundException;
import com.leaseguard.rag.client.RagServerClient;
import com.leaseguard.rag.dto.RagChatRequest;
import com.leaseguard.rag.dto.RagChatResponse;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ChatService {

    private static final int RAG_CHAT_HISTORY_LIMIT = 8;
    private static final int MEMORY_SUMMARY_MAX_LENGTH = 2_000;

    private final AnonymousSessionRepository anonymousSessionRepository;
    private final ContractService contractService;
    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final MessageSourceRepository messageSourceRepository;
    private final RagServerClient ragServerClient;
    private final ObjectMapper objectMapper;

    public ChatService(
            AnonymousSessionRepository anonymousSessionRepository,
            ContractService contractService,
            ChatSessionRepository chatSessionRepository,
            ChatMessageRepository chatMessageRepository,
            MessageSourceRepository messageSourceRepository,
            RagServerClient ragServerClient,
            ObjectMapper objectMapper
    ) {
        this.anonymousSessionRepository = anonymousSessionRepository;
        this.contractService = contractService;
        this.chatSessionRepository = chatSessionRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.messageSourceRepository = messageSourceRepository;
        this.ragServerClient = ragServerClient;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public ChatSessionResponse createChatSession(String anonymousSessionId, ChatSessionCreateRequest request) {
        AnonymousSession anonymousSession = findAnonymousSession(anonymousSessionId);
        Long requestContractId = request == null ? null : request.contractId();
        Contract contract = requestContractId == null
                ? null
                : contractService.findOwnedContract(anonymousSessionId, requestContractId);
        LocalDateTime now = LocalDateTime.now();

        ChatSession chatSession = chatSessionRepository.save(new ChatSession(
                anonymousSession,
                contract,
                request == null ? null : request.title(),
                now,
                now
        ));
        return ChatSessionResponse.from(chatSession);
    }

    @Transactional(readOnly = true)
    public List<ChatSessionResponse> getChatSessions(String anonymousSessionId) {
        ensureAnonymousSessionExists(anonymousSessionId);
        return chatSessionRepository.findByAnonymousSessionAnonymousSessionIdOrderByUpdatedAtDesc(anonymousSessionId)
                .stream()
                .map(ChatSessionResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<ChatMessageResponse> getMessages(String anonymousSessionId, Long chatSessionId) {
        findOwnedChatSession(anonymousSessionId, chatSessionId);
        return chatMessageRepository.findByChatSessionChatSessionIdOrderByCreatedAtAsc(chatSessionId)
                .stream()
                .map(message -> ChatMessageResponse.of(message, getSources(message)))
                .toList();
    }

    @Transactional
    public ChatAnswerResponse createMessage(
            String anonymousSessionId,
            Long chatSessionId,
            ChatMessageCreateRequest request
    ) {
        if (request == null || request.message() == null || request.message().isBlank()) {
            throw new BadRequestException("채팅 메시지를 입력해 주세요.");
        }

        ChatSession chatSession = findOwnedChatSession(anonymousSessionId, chatSessionId);
        Long contractId = resolveContractId(chatSession, request.contractId());
        if (contractId != null) {
            contractService.findOwnedContract(anonymousSessionId, contractId);
        }

        List<ChatMessage> previousMessages = chatMessageRepository
                .findByChatSessionChatSessionIdOrderByCreatedAtAsc(chatSessionId);

        ChatMessage userMessage = chatMessageRepository.save(new ChatMessage(
                chatSession,
                "user",
                request.message(),
                LocalDateTime.now()
        ));

        RagChatResponse ragResponse = ragServerClient.chat(new RagChatRequest(
                anonymousSessionId,
                contractId,
                request.message(),
                ragChatHistory(chatSession, previousMessages)
        ));

        ChatMessage assistantMessage = chatMessageRepository.save(new ChatMessage(
                chatSession,
                "assistant",
                ragResponse.answer(),
                LocalDateTime.now()
        ));

        List<MessageSourceResponse> sources = saveSources(assistantMessage, ragResponse.sources());
        LocalDateTime now = LocalDateTime.now();
        chatSession.updateMemorySummary(
                updateMemorySummary(chatSession.getMemorySummary(), request.message(), assistantMessage.getContent()),
                now
        );
        chatSession.touch(now);
        return new ChatAnswerResponse(assistantMessage.getContent(), sources);
    }

    private Long resolveContractId(ChatSession chatSession, Long requestContractId) {
        if (requestContractId != null) {
            return requestContractId;
        }
        return chatSession.getContract() == null ? null : chatSession.getContract().getContractId();
    }

    private List<ChatMessage> recentHistory(List<ChatMessage> messages) {
        List<ChatMessage> userAndAssistantMessages = messages.stream()
                .filter(message -> "user".equals(message.getRole()) || "assistant".equals(message.getRole()))
                .toList();
        int fromIndex = Math.max(0, userAndAssistantMessages.size() - RAG_CHAT_HISTORY_LIMIT);
        return userAndAssistantMessages.subList(fromIndex, userAndAssistantMessages.size());
    }

    private List<RagChatRequest.HistoryMessage> ragChatHistory(ChatSession chatSession, List<ChatMessage> previousMessages) {
        List<RagChatRequest.HistoryMessage> history = new ArrayList<>();
        if (chatSession.getMemorySummary() != null && !chatSession.getMemorySummary().isBlank()) {
            history.add(new RagChatRequest.HistoryMessage(
                    "assistant",
                    "STRUCTURED_CHAT_MEMORY_JSON\n" + chatSession.getMemorySummary()
            ));
        }
        history.addAll(recentHistory(previousMessages).stream()
                .map(message -> new RagChatRequest.HistoryMessage(message.getRole(), message.getContent()))
                .toList());
        return history;
    }

    private String updateMemorySummary(String previousSummary, String userMessage, String assistantAnswer) {
        ChatMemorySummary previousMemory = readMemorySummary(previousSummary);
        String combined = String.join("\n",
                previousMemory == null ? "" : String.join(" ", previousMemory.issueCategories()),
                previousMemory == null ? "" : previousMemory.latestUserConcern(),
                previousMemory == null ? "" : String.join(" ", previousMemory.recommendedNextActions()),
                userMessage,
                assistantAnswer
        );

        Set<String> issueCategories = new LinkedHashSet<>();
        if (previousMemory != null) {
            issueCategories.addAll(previousMemory.issueCategories());
        }
        addIssueIfMatched(issueCategories, combined, "deposit_return", List.of("보증금", "반환", "돌려받", "임차권등기"));
        addIssueIfMatched(issueCategories, combined, "special_clause", List.of("특약", "불리", "임차인 부담", "조항"));
        addIssueIfMatched(issueCategories, combined, "repair_cost_restoration", List.of("수리비", "수선", "원상복구", "노후화", "통상 사용"));
        addIssueIfMatched(issueCategories, combined, "move_in_fixed_date", List.of("전입신고", "확정일자", "대항력", "우선변제권"));
        addIssueIfMatched(issueCategories, combined, "registry_check", List.of("등기부", "근저당", "압류", "가압류", "선순위"));
        addIssueIfMatched(issueCategories, combined, "jeonse_fraud_prevention", List.of("전세사기", "보증보험", "시세", "전세가율"));
        addIssueIfMatched(issueCategories, combined, "legal_judgment_sensitive", List.of("무효", "위법", "소송", "승소", "패소", "사기"));

        ChatMemorySummary nextMemory = new ChatMemorySummary(
                inferTopic(issueCategories),
                List.copyOf(issueCategories),
                safeSnippet(userMessage, 300),
                recommendedNextActions(issueCategories)
        );

        try {
            return safeSnippet(objectMapper.writeValueAsString(nextMemory), MEMORY_SUMMARY_MAX_LENGTH);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("채팅 메모리 JSON 생성에 실패했습니다.", exception);
        }
    }

    private ChatMemorySummary readMemorySummary(String memorySummary) {
        if (memorySummary == null || memorySummary.isBlank()) {
            return null;
        }
        try {
            Map<String, Object> raw = objectMapper.readValue(memorySummary, new TypeReference<>() {
            });
            return new ChatMemorySummary(
                    stringValue(raw.get("topic")),
                    stringList(raw.get("issueCategories")),
                    stringValue(raw.get("latestUserConcern")),
                    stringList(raw.get("recommendedNextActions"))
            );
        } catch (JsonProcessingException exception) {
            return null;
        }
    }

    private void addIssueIfMatched(Set<String> issueCategories, String text, String issue, List<String> markers) {
        if (markers.stream().anyMatch(text::contains)) {
            issueCategories.add(issue);
        }
    }

    private String inferTopic(Set<String> issueCategories) {
        if (issueCategories.contains("legal_judgment_sensitive")) {
            return "legal_judgment_sensitive_contract_risk_check";
        }
        if (issueCategories.contains("deposit_return")) {
            return "deposit_return_risk_check";
        }
        if (issueCategories.contains("special_clause") || issueCategories.contains("repair_cost_restoration")) {
            return "special_clause_and_repair_risk_check";
        }
        if (issueCategories.contains("registry_check") || issueCategories.contains("jeonse_fraud_prevention")) {
            return "pre_contract_safety_check";
        }
        return "general_contract_risk_check";
    }

    private List<String> recommendedNextActions(Set<String> issueCategories) {
        List<String> actions = new ArrayList<>();
        if (issueCategories.contains("deposit_return")) {
            actions.add("보증금 반환 시점과 조건을 계약서 문구로 명확히 확인한다.");
        }
        if (issueCategories.contains("special_clause") || issueCategories.contains("repair_cost_restoration")) {
            actions.add("특약, 수리비, 원상복구 책임 범위를 임대인에게 문서로 확인한다.");
        }
        if (issueCategories.contains("move_in_fixed_date")) {
            actions.add("전입신고와 확정일자 처리 시점을 확인한다.");
        }
        if (issueCategories.contains("registry_check")) {
            actions.add("등기부등본에서 소유자, 근저당, 압류, 선순위 권리를 확인한다.");
        }
        if (issueCategories.contains("jeonse_fraud_prevention")) {
            actions.add("보증보험, 주변 시세, 전세가율 등 전세사기 예방 항목을 확인한다.");
        }
        if (issueCategories.contains("legal_judgment_sensitive")) {
            actions.add("무효, 위법, 소송 승패는 단정하지 않고 전문가 상담을 권장한다.");
        }
        if (actions.isEmpty()) {
            actions.add("계약서에서 날짜, 금액, 책임 주체가 모호한 표현을 우선 확인한다.");
        }
        return actions.stream().limit(5).toList();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private List<String> stringList(Object value) {
        if (value instanceof List<?> values) {
            return values.stream()
                    .map(String::valueOf)
                    .filter(item -> !item.isBlank())
                    .toList();
        }
        return List.of();
    }

    private String safeSnippet(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        String normalized = value.replaceAll("\\s+", " ").trim();
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, maxLength);
    }

    private List<MessageSourceResponse> saveSources(ChatMessage assistantMessage, List<RagChatResponse.Source> sources) {
        if (sources == null) {
            return List.of();
        }

        return sources.stream()
                .map(source -> messageSourceRepository.save(new MessageSource(
                        assistantMessage,
                        source.sourceType(),
                        source.sourceTitle(),
                        source.pageNumber(),
                        source.chunkText(),
                        source.similarityScore()
                )))
                .map(MessageSourceResponse::from)
                .toList();
    }

    private List<MessageSourceResponse> getSources(ChatMessage message) {
        if (!"assistant".equals(message.getRole())) {
            return List.of();
        }
        return messageSourceRepository.findByMessageMessageId(message.getMessageId())
                .stream()
                .map(MessageSourceResponse::from)
                .toList();
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

    private ChatSession findOwnedChatSession(String anonymousSessionId, Long chatSessionId) {
        ChatSession chatSession = chatSessionRepository.findById(chatSessionId)
                .orElseThrow(() -> new NotFoundException("채팅 세션을 찾을 수 없습니다."));
        if (!chatSession.getAnonymousSession().getAnonymousSessionId().equals(anonymousSessionId)) {
            throw new ForbiddenException("다른 익명 세션의 채팅 세션에는 접근할 수 없습니다.");
        }
        return chatSession;
    }

    private record ChatMemorySummary(
            String topic,
            List<String> issueCategories,
            String latestUserConcern,
            List<String> recommendedNextActions
    ) {
    }
}
