package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/** {@code POST /ai/{feature}} 계열 엔드포인트가 공통으로 돌려주는 접수증. */
public record AiJobCreatedResponse(@JsonProperty("job_id") String jobId) {
}
