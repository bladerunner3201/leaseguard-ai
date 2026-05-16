package com.leaseguard.chat.service;

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
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ChatService {

    private final AnonymousSessionRepository anonymousSessionRepository;
    private final ContractService contractService;
    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final MessageSourceRepository messageSourceRepository;
    private final RagServerClient ragServerClient;

    public ChatService(
            AnonymousSessionRepository anonymousSessionRepository,
            ContractService contractService,
            ChatSessionRepository chatSessionRepository,
            ChatMessageRepository chatMessageRepository,
            MessageSourceRepository messageSourceRepository,
            RagServerClient ragServerClient
    ) {
        this.anonymousSessionRepository = anonymousSessionRepository;
        this.contractService = contractService;
        this.chatSessionRepository = chatSessionRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.messageSourceRepository = messageSourceRepository;
        this.ragServerClient = ragServerClient;
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
                previousMessages.stream()
                        .map(message -> new RagChatRequest.HistoryMessage(message.getRole(), message.getContent()))
                        .toList()
        ));

        ChatMessage assistantMessage = chatMessageRepository.save(new ChatMessage(
                chatSession,
                "assistant",
                ragResponse.answer(),
                LocalDateTime.now()
        ));

        List<MessageSourceResponse> sources = saveSources(assistantMessage, ragResponse.sources());
        chatSession.touch(LocalDateTime.now());
        return new ChatAnswerResponse(assistantMessage.getContent(), sources);
    }

    private Long resolveContractId(ChatSession chatSession, Long requestContractId) {
        if (requestContractId != null) {
            return requestContractId;
        }
        return chatSession.getContract() == null ? null : chatSession.getContract().getContractId();
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
}
