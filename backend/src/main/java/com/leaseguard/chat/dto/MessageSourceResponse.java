package com.leaseguard.chat.dto;

import com.leaseguard.chat.entity.MessageSource;
import com.leaseguard.rag.dto.RagChatResponse;

public record MessageSourceResponse(
        String sourceType,
        String sourceTitle,
        Integer pageNumber,
        String chunkText,
        Double similarityScore
) {
    public static MessageSourceResponse from(MessageSource source) {
        return new MessageSourceResponse(
                source.getSourceType(),
                source.getSourceTitle(),
                source.getPageNumber(),
                source.getChunkText(),
                source.getSimilarityScore()
        );
    }

    public static MessageSourceResponse from(RagChatResponse.Source source) {
        return new MessageSourceResponse(
                source.sourceType(),
                source.sourceTitle(),
                source.pageNumber(),
                source.chunkText(),
                source.similarityScore()
        );
    }
}
