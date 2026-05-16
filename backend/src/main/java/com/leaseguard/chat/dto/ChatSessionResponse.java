package com.leaseguard.chat.dto;

import com.leaseguard.chat.entity.ChatSession;
import java.time.LocalDateTime;

public record ChatSessionResponse(
        Long chatSessionId,
        Long contractId,
        String title,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
    public static ChatSessionResponse from(ChatSession chatSession) {
        Long contractId = chatSession.getContract() == null ? null : chatSession.getContract().getContractId();
        return new ChatSessionResponse(
                chatSession.getChatSessionId(),
                contractId,
                chatSession.getTitle(),
                chatSession.getCreatedAt(),
                chatSession.getUpdatedAt()
        );
    }
}
