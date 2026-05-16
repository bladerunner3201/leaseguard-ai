package com.leaseguard.anonymous.service;

import com.leaseguard.anonymous.dto.AnonymousSessionCreateResponse;
import com.leaseguard.anonymous.entity.AnonymousSession;
import com.leaseguard.anonymous.repository.AnonymousSessionRepository;
import java.time.LocalDateTime;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnonymousSessionService {

    private final AnonymousSessionRepository anonymousSessionRepository;

    public AnonymousSessionService(AnonymousSessionRepository anonymousSessionRepository) {
        this.anonymousSessionRepository = anonymousSessionRepository;
    }

    @Transactional
    public AnonymousSessionCreateResponse createAnonymousSession(String userAgent, String ipAddress) {
        LocalDateTime now = LocalDateTime.now();
        AnonymousSession anonymousSession = new AnonymousSession(
                UUID.randomUUID().toString(),
                now,
                now,
                userAgent,
                ipAddress
        );

        AnonymousSession savedSession = anonymousSessionRepository.save(anonymousSession);
        return new AnonymousSessionCreateResponse(savedSession.getAnonymousSessionId());
    }
}
