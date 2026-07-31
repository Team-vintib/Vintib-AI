package com.ssafy.backend.member.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import java.util.List;

/**
 * ONBOARD-002 / MY-001: 관심 브랜드·카테고리 등록·수정 요청 DTO.
 * 선택 입력이라 빈 리스트(건너뛰기)는 허용하지만, 리스트 자체는 항상 보내야 한다(전체 교체 방식).
 */
public record UpdateInterestsRequest(

        @Schema(description = "관심 브랜드 ID 목록 (선택, 건너뛰려면 빈 배열)", example = "[1, 2]")
        @NotNull(message = "brandIds는 필수입니다(빈 배열은 허용).")
        List<@NotNull Long> brandIds,

        @Schema(description = "관심 카테고리 ID 목록 (선택, 건너뛰려면 빈 배열)", example = "[3, 5]")
        @NotNull(message = "categoryIds는 필수입니다(빈 배열은 허용).")
        List<@NotNull Long> categoryIds
) {
}
