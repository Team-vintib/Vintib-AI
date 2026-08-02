package com.ssafy.backend.member.dto.response;

import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberStatus;
import com.ssafy.backend.member.entity.MemberType;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 회원 기본 정보 응답 DTO (ONBOARD-001 결과, MY-001 조회).
 */
public record MemberProfileResponse(

        @Schema(example = "1")
        Long id,

        @Schema(example = "user@example.com")
        String email,

        @Schema(example = "홍길동")
        String name,

        @Schema(example = "빈티지헌터")
        String nickname,

        @Schema(example = "01012345678")
        String phoneNumber,

        @Schema(example = "서울시 강남구 테헤란로 123")
        String address,

        @Schema(example = "3층")
        String detailAddress,

        @Schema(example = "06236")
        String postalCode,

        @Schema(example = "MALE")
        Gender gender,

        @Schema(example = "GENERAL")
        MemberType memberType,

        @Schema(example = "ACTIVE")
        MemberStatus status,

        @Schema(example = "true")
        boolean onboardingCompleted,

        @Schema(description = "NONE(미제출) | PENDING | APPROVED | REJECTED", example = "NONE")
        String businessVerificationStatus
) {

    public static MemberProfileResponse from(Member member, String businessVerificationStatus) {
        return new MemberProfileResponse(
                member.getId(),
                member.getEmail(),
                member.getName(),
                member.getNickname(),
                member.getPhoneNumber(),
                member.getAddress(),
                member.getDetailAddress(),
                member.getPostalCode(),
                member.getGender(),
                member.getMemberType(),
                member.getStatus(),
                member.isOnboardingCompleted(),
                businessVerificationStatus
        );
    }
}
