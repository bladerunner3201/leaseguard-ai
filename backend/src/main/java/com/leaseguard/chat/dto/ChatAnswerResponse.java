package com.leaseguard.chat.dto;

import java.util.List;

public record ChatAnswerResponse(
        String answer,
        List<MessageSourceResponse> sources
) {
}
