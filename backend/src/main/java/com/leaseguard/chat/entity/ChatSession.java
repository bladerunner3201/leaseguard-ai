package com.leaseguard.chat.entity;

import com.leaseguard.anonymous.entity.AnonymousSession;
import com.leaseguard.contract.entity.Contract;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "chat_sessions")
public class ChatSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "chat_session_id")
    private Long chatSessionId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "anonymous_session_id", nullable = false)
    private AnonymousSession anonymousSession;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "contract_id")
    private Contract contract;

    @Column(name = "title")
    private String title;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    protected ChatSession() {
    }

    public ChatSession(
            AnonymousSession anonymousSession,
            Contract contract,
            String title,
            LocalDateTime createdAt,
            LocalDateTime updatedAt
    ) {
        this.anonymousSession = anonymousSession;
        this.contract = contract;
        this.title = title;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getChatSessionId() {
        return chatSessionId;
    }

    public AnonymousSession getAnonymousSession() {
        return anonymousSession;
    }

    public Contract getContract() {
        return contract;
    }

    public String getTitle() {
        return title;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void touch(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
