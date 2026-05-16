package com.leaseguard.anonymous.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "anonymous_sessions")
public class AnonymousSession {

    @Id
    @Column(name = "anonymous_session_id", length = 36, nullable = false)
    private String anonymousSessionId;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "last_accessed_at", nullable = false)
    private LocalDateTime lastAccessedAt;

    @Column(name = "user_agent", length = 500)
    private String userAgent;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    protected AnonymousSession() {
    }

    public AnonymousSession(
            String anonymousSessionId,
            LocalDateTime createdAt,
            LocalDateTime lastAccessedAt,
            String userAgent,
            String ipAddress
    ) {
        this.anonymousSessionId = anonymousSessionId;
        this.createdAt = createdAt;
        this.lastAccessedAt = lastAccessedAt;
        this.userAgent = userAgent;
        this.ipAddress = ipAddress;
    }

    public String getAnonymousSessionId() {
        return anonymousSessionId;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getLastAccessedAt() {
        return lastAccessedAt;
    }

    public String getUserAgent() {
        return userAgent;
    }

    public String getIpAddress() {
        return ipAddress;
    }
}
