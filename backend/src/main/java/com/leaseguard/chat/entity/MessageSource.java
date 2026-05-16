package com.leaseguard.chat.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "message_sources")
public class MessageSource {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "source_id")
    private Long sourceId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "message_id", nullable = false)
    private ChatMessage message;

    @Column(name = "source_type", length = 30)
    private String sourceType;

    @Column(name = "source_title")
    private String sourceTitle;

    @Column(name = "page_number")
    private Integer pageNumber;

    @Column(name = "chunk_text", columnDefinition = "TEXT")
    private String chunkText;

    @Column(name = "similarity_score")
    private Double similarityScore;

    protected MessageSource() {
    }

    public MessageSource(
            ChatMessage message,
            String sourceType,
            String sourceTitle,
            Integer pageNumber,
            String chunkText,
            Double similarityScore
    ) {
        this.message = message;
        this.sourceType = sourceType;
        this.sourceTitle = sourceTitle;
        this.pageNumber = pageNumber;
        this.chunkText = chunkText;
        this.similarityScore = similarityScore;
    }

    public Long getSourceId() {
        return sourceId;
    }

    public String getSourceType() {
        return sourceType;
    }

    public String getSourceTitle() {
        return sourceTitle;
    }

    public Integer getPageNumber() {
        return pageNumber;
    }

    public String getChunkText() {
        return chunkText;
    }

    public Double getSimilarityScore() {
        return similarityScore;
    }
}
