package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

public record ProductUpdateRequest(
        @Size(min = 1) String title,
        String description,
        Long categoryId,
        Long brandId,
        String conditionGrade,
        String sizeLabel,

        @Schema(example = "BLACK") String color,

        @Schema(example = "Cotton 100%") String material,

        @Schema(description = "실측 치수(cm). null이면 미반영", example = "{\"총장\": 70, \"어깨너비\": 45}")
        Map<String, Integer> measurements,

        @Schema(
                description = "하자 목록 전체 교체. null이면 미반영, 빈 배열이면 기존 하자를 전부 삭제한다.",
                example = "[\"소매 끝 실밥 풀림\"]")
        List<String> defects) {
}