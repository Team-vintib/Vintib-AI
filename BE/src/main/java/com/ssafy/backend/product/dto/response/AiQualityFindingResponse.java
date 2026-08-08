package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.ProductQualityFinding;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.Map;

public record AiQualityFindingResponse(
        @Schema(example = "옅은 갈색 얼룩이 확인됩니다.") String description,
        @Schema(description = "검수 이미지 위 탐지 위치(프레임 기준 %, 0~100). 없으면 null")
                Map<String, Integer> box) {

    public static AiQualityFindingResponse from(ProductQualityFinding finding) {
        return new AiQualityFindingResponse(finding.getDescription(), finding.getBox());
    }
}
