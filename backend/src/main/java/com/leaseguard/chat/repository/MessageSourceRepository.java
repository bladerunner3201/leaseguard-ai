package com.leaseguard.chat.repository;

import com.leaseguard.chat.entity.MessageSource;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MessageSourceRepository extends JpaRepository<MessageSource, Long> {

    List<MessageSource> findByMessageMessageId(Long messageId);
}
