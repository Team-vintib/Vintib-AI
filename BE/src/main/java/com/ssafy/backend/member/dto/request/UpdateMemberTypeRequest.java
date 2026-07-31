package com.ssafy.backend.member.dto.request;

import com.ssafy.backend.member.entity.MemberType;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * ONBOARD-004: 회원 유형(일반/사업자) 저장 및 온보딩 완료 요청 DTO.
 */
public record UpdateMemberTypeRequest(

        @Schema(description = "회원 유형 (GENERAL/BUSINESS)", example = "GENERAL")
        @NotNull(message = "회원 유형은 필수입니다.")
        MemberType memberType
) {
}
