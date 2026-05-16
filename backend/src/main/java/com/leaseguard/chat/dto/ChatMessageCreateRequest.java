package com.leaseguard.chat.dto;

public record ChatMessageCreateRequest(
        Long contractId,
        String message
) {
}
