package com.ssafy.backend.tryon.dto.response;

import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.entity.TryOnResultStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record TryOnResultResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "1") Long productId,
        @Schema(description = "PENDING/PROCESSING이면 아직 완료 전, imageUrl은 null", example = "SUCCESS")
                TryOnResultStatus status,
        @Schema(example = "https://s3.example.com/tryon-results/1/abc123.jpg?X-Amz-...") String imageUrl,
        @Schema(description = "한 줄 핏 예상 제목. 실측 부족 시 null", example = "선택하신 사이즈가 살짝 타이트해요.")
                String fitTitle,
        @Schema(description = "한 줄 핏 예상 설명. 실측 부족 시 null",
                example = "허리 부분이 살짝 붙는 느낌으로 예상돼요 (기준보다 약 12% 작아요).")
                String fitDescription,
        @Schema(description = "결과 상품의 대분류 카테고리 ID(상의/하의/아우터/원피스/신발/가방/액세서리 등 depth=2). "
                        + "카테고리를 못 찾으면 null.", example = "12")
                Long categoryId,
        @Schema(description = "결과 상품의 대분류 카테고리 이름. 카테고리를 못 찾으면 null.", example = "아우터")
                String categoryName,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt) {

    public static TryOnResultResponse of(TryOnResult result, String imageUrl, TopCategory topCategory) {
        return new TryOnResultResponse(
                result.getId(),
                result.getProduct().getId(),
                result.getStatus(),
                imageUrl,
                result.getFitTitle(),
                result.getFitDescription(),
                topCategory != null ? topCategory.id() : null,
                topCategory != null ? topCategory.name() : null,
                result.getCreatedAt());
    }

    /** 결과 상품의 대분류(depth=2) 카테고리 — {@link com.ssafy.backend.tryon.service.TryOnResultService} 참고. */
    public record TopCategory(Long id, String name) {
    }
}
