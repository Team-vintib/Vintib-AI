package com.ssafy.backend.order.dto.response;

import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.product.dto.response.ProductResponse;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 마이페이지 구매 내역(MY-003)·판매/정산 내역(MY-004) 공용 목록 카드.
 * 구매자/판매자 관점 둘 다 한 화면에서 쓸 수 있게 양쪽 정보를 함께 담는다.
 */
public record OrderListItemResponse(
        @Schema(example = "10") Long orderId,
        ProductResponse product,
        @Schema(example = "1") Long buyerId,
        @Schema(example = "구매자닉네임") String buyerNickname,
        @Schema(example = "2") Long sellerId,
        @Schema(example = "판매자닉네임") String sellerNickname,
        @Schema(example = "110000") Long orderPrice,
        @Schema(example = "PAID") String status,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime createdAt) {

    public static OrderListItemResponse from(Order order) {
        return new OrderListItemResponse(
                order.getId(),
                ProductResponse.from(order.getProduct()),
                order.getBuyer().getId(),
                order.getBuyer().getNickname(),
                order.getSeller().getId(),
                order.getSeller().getNickname(),
                order.getOrderPrice(),
                order.getStatus().name(),
                order.getCreatedAt());
    }
}
