package com.leaseguard.anonymous.controller;

import com.leaseguard.global.response.ApiResponse;
import java.util.UUID;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/anonymous-sessions")
public class AnonymousSessionController {

    @PostMapping
    public ApiResponse<AnonymousSessionResponse> createAnonymousSession() {
        return ApiResponse.ok(new AnonymousSessionResponse(UUID.randomUUID().toString()));
    }

    public record AnonymousSessionResponse(String anonymousSessionId) {
    }
}
