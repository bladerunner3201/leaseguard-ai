package com.leaseguard.rag.client;

import com.leaseguard.rag.dto.ContractAnalyzeRequest;
import com.leaseguard.rag.dto.ContractAnalyzeResponse;
import com.leaseguard.rag.dto.RagChatRequest;
import com.leaseguard.rag.dto.RagChatResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class RagServerClient {

    private final RestClient restClient;

    public RagServerClient(
            RestClient.Builder restClientBuilder,
            @Value("${rag.server.base-url}") String ragServerBaseUrl
    ) {
        this.restClient = restClientBuilder
                .baseUrl(ragServerBaseUrl)
                .build();
    }

    public ContractAnalyzeResponse indexContract(ContractAnalyzeRequest request) {
        return restClient.post()
                .uri("/rag/contracts/index")
                .body(request)
                .retrieve()
                .body(ContractAnalyzeResponse.class);
    }

    public RagChatResponse chat(RagChatRequest request) {
        return restClient.post()
                .uri("/rag/chat")
                .body(request)
                .retrieve()
                .body(RagChatResponse.class);
    }
}
