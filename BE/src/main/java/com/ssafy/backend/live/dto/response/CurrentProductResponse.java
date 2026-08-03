package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 소개 중인 상품 전환 알림. {@code /topic/lives/{liveId}/product} 로 나간다.
 *
 * <p><b>상품 정보를 통째로 싣지 않고 ID만 보낸다.</b> 편성 상품의 상세는 시청 화면 진입 시
 * 라이브 상세 응답으로 이미 받아 뒀다. 전환할 때마다 같은 내용을 다시 보내면 모든 시청자에게
 * 중복 payload가 나가고, 상품 정보가 두 경로로 들어와 어느 쪽이 최신인지 모호해진다.
 *
 * <p>FE는 이 ID로 <b>이미 갖고 있는 편성 목록에서 찾아</b> NOW 배지를 옮기면 된다.
 */
public record CurrentProductResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(
                description = "지금 소개 중인 상품 ID. **null이면 소개 중인 상품이 없다** "
                        + "(호스트가 해제했거나 방송이 끝났다)",
                example = "2001")
        Long currentProductId
) {

    public static CurrentProductResponse of(Long liveId, Long currentProductId) {
        return new CurrentProductResponse(liveId, currentProductId);
    }
}
