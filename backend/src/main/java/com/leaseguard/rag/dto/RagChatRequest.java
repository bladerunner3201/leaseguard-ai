package com.leaseguard.rag.dto;

import java.util.List;

public record RagChatRequest(
        String anonymousSessionId,
        Long contractId,
        String message,
        List<HistoryMessage> chatHistory
) {
    public record HistoryMessage(String role, String content) {
    }
}
