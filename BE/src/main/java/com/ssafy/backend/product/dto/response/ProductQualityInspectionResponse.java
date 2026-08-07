package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.QualityInspectionStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.Map;

public record ProductQualityInspectionResponse(
        @Schema(description = "NONE=대상 아님/미시작, PENDING/PROCESSING=검수 중, COMPLETED=완료, FAILED=실패",
                example = "PROCESSING")
                QualityInspectionStatus status,
        @Schema(description = "status=COMPLETED일 때만 값 존재. AI 검수 결과(condition_score/condition_grade/"
                + "findings 등) 원본 — `docs/requests/BE/041` §2 참고")
                Map<String, Object> result) {

    public static ProductQualityInspectionResponse from(Product product) {
        return new ProductQualityInspectionResponse(
                product.getQualityInspectionStatus(), product.getQualityInspectionResult());
    }
}
