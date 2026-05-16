package com.leaseguard.document.controller;

import com.leaseguard.global.response.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/documents")
public class DocumentController {

    @GetMapping("/health")
    public ApiResponse<String> healthCheck() {
        return ApiResponse.ok("document package ready");
    }
}
