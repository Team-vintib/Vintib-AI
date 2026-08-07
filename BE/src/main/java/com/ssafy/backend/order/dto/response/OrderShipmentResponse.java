package com.ssafy.backend.order.dto.response;

import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.OrderShipment;
import com.ssafy.backend.order.entity.TrackingStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record OrderShipmentResponse(
        @Schema(example = "홍길동") String recipientName,
        @Schema(example = "010-1234-5678") String recipientPhone,
        @Schema(example = "06134") String zipcode,
        @Schema(example = "서울특별시 강남구 테헤란로 1") String address1,
        @Schema(example = "101동 1001호") String address2,
        @Schema(example = "CJ") CourierCode courierCode,
        @Schema(example = "CJ대한통운") String courierName,
        @Schema(example = "123456789012") String trackingNumber,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime shippedAt,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime deliveredAt,
        @Schema(description = "배송 진행 상태. 송장 등록 직후 첫 웹훅 전에는 null", example = "IN_TRANSIT")
        TrackingStatus trackingStatus,
        @Schema(description = "배송 진행 상태 한글 표시", example = "배송중") String trackingStatusLabel) {

    public static OrderShipmentResponse from(OrderShipment shipment) {
        CourierCode courier = shipment.getCourier();
        TrackingStatus status = shipment.getTrackingStatus();
        return new OrderShipmentResponse(
                shipment.getRecipientName(),
                shipment.getRecipientPhone(),
                shipment.getZipcode(),
                shipment.getAddress1(),
                shipment.getAddress2(),
                courier,
                courier == null ? null : courier.getDisplayName(),
                shipment.getTrackingNumber(),
                shipment.getShippedAt(),
                shipment.getDeliveredAt(),
                status,
                status == null ? null : status.getDisplayName());
    }
}