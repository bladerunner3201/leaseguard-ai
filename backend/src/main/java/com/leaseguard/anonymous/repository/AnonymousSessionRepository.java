package com.leaseguard.anonymous.repository;

import com.leaseguard.anonymous.entity.AnonymousSession;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AnonymousSessionRepository extends JpaRepository<AnonymousSession, String> {
}
