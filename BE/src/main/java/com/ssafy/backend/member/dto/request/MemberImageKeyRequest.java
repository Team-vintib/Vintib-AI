package com.ssafy.backend.member.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/**
 * 프로필/커버 이미지 확정 요청(011 §5) — presigned 업로드 1단계에서 받은 key를 그대로 보낸다.
 */
public record MemberImageKeyRequest(

        @Schema(example = "member-profiles/1/abc123.jpg")
        @NotBlank
        String key) {
}
