package com.leaseguard.chat.dto;

import com.leaseguard.chat.entity.ChatMessage;
import java.time.LocalDateTime;
import java.util.List;

public record ChatMessageResponse(
        Long messageId,
        String role,
        String content,
        LocalDateTime createdAt,
        List<MessageSourceResponse> sources
) {
    public static ChatMessageResponse of(ChatMessage message, List<MessageSourceResponse> sources) {
        return new ChatMessageResponse(
                message.getMessageId(),
                message.getRole(),
                message.getContent(),
                message.getCreatedAt(),
                sources
        );
    }
}
