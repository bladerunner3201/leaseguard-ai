package com.leaseguard.rag.dto;

import java.util.List;

public record RagChatResponse(
        String answer,
        List<Source> sources
) {
    public record Source(
            String sourceType,
            String sourceTitle,
            Integer pageNumber,
            String chunkText,
            Double similarityScore
    ) {
    }
}
