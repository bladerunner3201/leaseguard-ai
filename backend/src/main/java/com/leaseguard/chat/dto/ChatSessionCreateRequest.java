package com.leaseguard.chat.dto;

public record ChatSessionCreateRequest(
        Long contractId,
        String title
) {
}
