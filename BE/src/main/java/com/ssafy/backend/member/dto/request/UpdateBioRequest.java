package com.ssafy.backend.member.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Size;

/**
 * 소개글 수정 요청 DTO(011 §5). 선택 입력이며, {@link UpdateMemberRequest}와 마찬가지로
 * 부분 수정이 아니라 매번 전체를 새로 받는다(값을 안 보내면 지워진다).
 *
 * <p>커버 이미지는 이 DTO가 아니라 {@code PUT /users/{id}/cover-image}(SY030, presigned 업로드
 * 확정)로 관리한다 — 처음엔 이 DTO가 원시 URL 문자열을 직접 받았으나, 실제 업로드 플로우가
 * 생기면서 그 방식으로 대체했다(breaking change, FE 미사용 확인 후 반영).
 */
public record UpdateBioRequest(

        @Schema(description = "소개글 (최대 500자)", example = "빈티지 셀러입니다.")
        @Size(max = 500, message = "소개글은 500자 이하로 입력해주세요.")
        String description
) {
}
