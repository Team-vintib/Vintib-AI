package com.ssafy.backend.global.client.dto;

import java.util.Map;

/**
 * {@code GET /ai/jobs/{job_id}} 응답 — 모든 AI 기능이 공유하는 공통 job 계약
 * (`AI/docs/infra-architecture.md` §5). {@code status}는 {@code queued|processing|success|failed}.
 */
public record AiJobResponse(String status, Map<String, Object> result, String error) {

    public boolean isSuccess() {
        return "success".equals(status);
    }

    public boolean isFailed() {
        return "failed".equals(status);
    }

    public boolean isDone() {
        return isSuccess() || isFailed();
    }
}
