package com.ssafy.backend.product.dto.response;

/**
 * 사전업로드 분류 job의 FE 노출용 상태. 엔티티 컬럼이 아니다(무상태 프록시라 저장하지 않음) —
 * AI 게이트웨이의 {@code queued|processing|success|failed}를 {@code QualityInspectionStatus}와
 * 같은 어휘(PENDING/PROCESSING/COMPLETED/FAILED)로 옮겨 응답한다.
 */
public enum ProductClassifyStatus {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED;

    public static ProductClassifyStatus fromAiStatus(String aiStatus) {
        return switch (aiStatus) {
            case "queued" -> PENDING;
            case "processing" -> PROCESSING;
            case "success" -> COMPLETED;
            default -> FAILED;
        };
    }
}
