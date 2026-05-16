package com.leaseguard.chat.controller;

import com.leaseguard.chat.dto.ChatAnswerResponse;
import com.leaseguard.chat.dto.ChatMessageCreateRequest;
import com.leaseguard.chat.dto.ChatMessageResponse;
import com.leaseguard.chat.dto.ChatSessionCreateRequest;
import com.leaseguard.chat.dto.ChatSessionResponse;
import com.leaseguard.chat.service.ChatService;
import com.leaseguard.global.response.ApiResponse;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/chat-sessions")
public class ChatController {

    private static final String SESSION_HEADER = "X-Anonymous-Session-Id";

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ApiResponse<ChatSessionResponse> createChatSession(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @RequestBody ChatSessionCreateRequest request
    ) {
        return ApiResponse.ok(chatService.createChatSession(anonymousSessionId, request));
    }

    @GetMapping
    public ApiResponse<List<ChatSessionResponse>> getChatSessions(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId
    ) {
        return ApiResponse.ok(chatService.getChatSessions(anonymousSessionId));
    }

    @GetMapping("/{chatSessionId}/messages")
    public ApiResponse<List<ChatMessageResponse>> getMessages(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long chatSessionId
    ) {
        return ApiResponse.ok(chatService.getMessages(anonymousSessionId, chatSessionId));
    }

    @PostMapping("/{chatSessionId}/messages")
    public ApiResponse<ChatAnswerResponse> createMessage(
            @RequestHeader(SESSION_HEADER) String anonymousSessionId,
            @PathVariable Long chatSessionId,
            @RequestBody ChatMessageCreateRequest request
    ) {
        return ApiResponse.ok(chatService.createMessage(anonymousSessionId, chatSessionId, request));
    }
}
