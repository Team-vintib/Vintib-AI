package com.ssafy.backend.member.dto.request;

import com.ssafy.backend.member.entity.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * ONBOARD-001 / MY-001: 닉네임·전화번호·주소·성별 등록·수정 요청 DTO.
 * 닉네임·전화번호·주소는 항상 새 값 전체를 받아 덮어쓴다(필수 입력). 성별만 선택 입력이며,
 * 보내지 않으면(null) 기존 값을 유지한다.
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

        @Schema(description = "성별 (MALE/FEMALE/OTHER)", example = "MALE")
        Gender gender
) {
}
