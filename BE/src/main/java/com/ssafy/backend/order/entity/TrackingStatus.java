package com.ssafy.backend.order.entity;

import lombok.Getter;

/** 배송 진행 상태(deliveryapi.co.kr). 웹훅 payload의 status 코드 그대로 12개. */
@Getter
public enum TrackingStatus {

    PENDING("접수 대기"),
    REGISTERED("접수 완료"),
    PICKUP_READY("집하 준비"),
    PICKED_UP("집하 완료"),
    IN_TRANSIT("배송중"),
    OUT_FOR_DELIVERY("배송 출발"),
    DELIVERED("배송 완료"),
    FAILED("배송 실패"),
    RETURNED("반송"),
    CANCELLED("취소"),
    HOLD("보류"),
    UNKNOWN("알 수 없음");

    /** deliveryapi.co.kr 웹훅의 status 값과 이름이 그대로 같다(대문자 스네이크 표기 동일). */
    private final String displayName;

    TrackingStatus(String displayName) {
        this.displayName = displayName;
    }

    /** 웹훅 payload의 status(예: "IN_TRANSIT")로 역매핑한다. 일치하는 게 없으면 null. */
    public static TrackingStatus fromApiCode(String apiCode) {
        for (TrackingStatus value : values()) {
            if (value.name().equals(apiCode)) {
                return value;
            }
        }
        return null;
    }
}