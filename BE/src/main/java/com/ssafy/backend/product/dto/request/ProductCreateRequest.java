package com.ssafy.backend.product.dto.request;

import com.ssafy.backend.product.entity.AiModelGender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;

public record ProductCreateRequest(

        @Schema(example = "Maison Kitsuné 더블 폭스 헤드 패치 클래식 티셔츠 블랙")
        @NotBlank
        String title,

        @Schema(example = "시착 0회. 더블 폭스 헤드 자수 패치. Maison Kitsuné Paris 정품.")
        String description,

        @Schema(description = "카테고리 ID. 필수다", example = "1")
        @NotNull
        Long categoryId,

        @Schema(example = "1")
        Long brandId,

        @Schema(example = "A")
        String conditionGrade,

        @Schema(example = "M")
        String sizeLabel,

        @Schema(example = "BLACK")
        String color,

        @Schema(example = "Cotton 100%")
        String material,

        @Schema(description = "실측 치수(cm). 선택 입력", example = "{\"총장\": 70, \"어깨너비\": 45}")
        Map<String, Integer> measurements,

        @Schema(description = "판매자가 직접 입력한 하자 목록. 선택 입력", example = "[\"소매 끝 실밥 풀림\"]")
        List<String> defects,

        @Schema(description = "마네킹 사진 기반 AI 착용컷 사용 여부", example = "true")
        boolean aiModelEnabled,

        @Schema(
                description = "AI 착용컷 모델 성별. aiModelEnabled=true면 필수, false면 null",
                example = "FEMALE")
        AiModelGender aiModelGender) {
}
