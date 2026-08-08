package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * {@code POST /ai/{feature}} 계열 엔드포인트가 공통으로 돌려주는 접수증.
 *
 * <p>{@code ignoreUnknown}: {@code POST /pricing/estimates}는 같은 모양에
 * {@code product_id}(에코)까지 얹어 돌려준다 — BE는 그 값이 필요 없어 필드를 추가하는 대신
 * 무시한다.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AiJobCreatedResponse(@JsonProperty("job_id") String jobId) {
}