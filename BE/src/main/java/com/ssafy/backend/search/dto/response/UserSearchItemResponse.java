package com.ssafy.backend.search.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 검색 결과의 회원 카드 한 장(SEARCH-001).
 *
 * <p>공개 프로필로 이동할 수 있는 최소 정보만 담는다 — 이메일·실명 같은 개인정보는 검색
 * 결과에 절대 싣지 않는다.
 */
public record UserSearchItemResponse(

        @Schema(description = "회원 ID", example = "31")
        Long id,

        @Schema(description = "닉네임", example = "빈티지장인")
        String nickname,

        @Schema(description = "프로필 이미지 URL. 등록하지 않았으면 null")
        String profileImageUrl,

        @Schema(description = "팔로워 수", example = "1284")
        Integer followerCount,

        @Schema(description = "판매 중인 상품 수(임시 저장 제외)", example = "37")
        Integer productCount,

        @Schema(
                description = "내가 팔로우 중인지. **비회원 요청이면 null**이며 FE는 팔로우 버튼을 "
                        + "비활성으로 둔다 — false로 내리면 '팔로우 가능'으로 오해한다",
                example = "false")
        Boolean isFollowing
) {
}
