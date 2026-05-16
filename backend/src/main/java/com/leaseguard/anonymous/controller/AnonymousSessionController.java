package com.leaseguard.anonymous.controller;

import com.leaseguard.anonymous.dto.AnonymousSessionCreateResponse;
import com.leaseguard.anonymous.service.AnonymousSessionService;
import com.leaseguard.global.response.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/anonymous-sessions")
public class AnonymousSessionController {

    private final AnonymousSessionService anonymousSessionService;

    public AnonymousSessionController(AnonymousSessionService anonymousSessionService) {
        this.anonymousSessionService = anonymousSessionService;
    }

    @PostMapping
    public ApiResponse<AnonymousSessionCreateResponse> createAnonymousSession(HttpServletRequest request) {
        String userAgent = request.getHeader(HttpHeaders.USER_AGENT);
        String ipAddress = extractClientIp(request);
        return ApiResponse.ok(anonymousSessionService.createAnonymousSession(userAgent, ipAddress));
    }

    private String extractClientIp(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            return forwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
