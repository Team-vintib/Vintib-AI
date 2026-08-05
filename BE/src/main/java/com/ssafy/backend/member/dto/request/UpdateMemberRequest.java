package com.ssafy.backend.member.dto.request;

import com.ssafy.backend.member.entity.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * ONBOARD-001 / MY-001: 닉네임·전화번호·주소·상세주소·성별 등록·수정 요청 DTO.
 * 우편번호(postalCode)를 제외한 전부 필수 입력이다 — 이 엔드포인트는 부분 수정이 아니라
 * 온보딩 기본 정보 전체를 매번 새로 받는다.
 */
public record UpdateMemberRequest(

        @Schema(description = "닉네임 (최대 30자)", example = "빈티지헌터")
        @NotBlank(message = "닉네임은 필수입니다.")
        @Size(max = 30, message = "닉네임은 30자 이하로 입력해주세요.")
        String nickname,

        @Schema(description = "전화번호 (숫자만, 10~11자리)", example = "01012345678")
        @NotBlank(message = "전화번호는 필수입니다.")
        @Pattern(
                regexp = "^\\d{10,11}$",
                message = "전화번호는 숫자만 10~11자리로 입력해주세요."
        )
        String phoneNumber,

        @Schema(description = "주소", example = "서울시 강남구 테헤란로 123")
        @NotBlank(message = "주소는 필수입니다.")
        @Size(max = 200, message = "주소는 200자 이하로 입력해주세요.")
        String address,

        @Schema(description = "상세주소", example = "3층")
        @NotBlank(message = "상세주소는 필수입니다.")
        @Size(max = 100, message = "상세주소는 100자 이하로 입력해주세요.")
        String detailAddress,

        @Schema(description = "우편번호. 주소 검색을 쓰면 채워지고, 직접 입력이면 없을 수 있다(선택)", example = "06236")
        @Size(max = 10, message = "우편번호는 10자 이하로 입력해주세요.")
        String postalCode,

        @Schema(description = "성별 (MALE/FEMALE)", example = "MALE")
        @NotNull(message = "성별은 필수입니다.")
        Gender gender
) {
}
