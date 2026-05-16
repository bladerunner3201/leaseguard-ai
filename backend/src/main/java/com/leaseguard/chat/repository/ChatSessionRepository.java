package com.leaseguard.chat.repository;

import com.leaseguard.chat.entity.ChatSession;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {

    List<ChatSession> findByAnonymousSessionAnonymousSessionIdOrderByUpdatedAtDesc(String anonymousSessionId);

    Optional<ChatSession> findByChatSessionIdAndAnonymousSessionAnonymousSessionId(
            Long chatSessionId,
            String anonymousSessionId
    );
}
