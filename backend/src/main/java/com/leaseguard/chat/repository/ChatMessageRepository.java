package com.leaseguard.chat.repository;

import com.leaseguard.chat.entity.ChatMessage;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    List<ChatMessage> findByChatSessionChatSessionIdOrderByCreatedAtAsc(Long chatSessionId);
}
