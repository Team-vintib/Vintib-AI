package com.ssafy.backend.order.entity;

import lombok.Getter;

/** 택배사(SHIP-001). deliveryapi.co.kr이 지원하는 국내 택배사 10개로 한정한다(자유 문자열 금지). */
@Getter
public enum CourierCode {

    LOTTE("lotte", "롯데택배"),
    CJ("cj", "CJ대한통운"),
    HANJIN("hanjin", "한진택배"),
    POST("post", "우체국택배"),
    KYUNGDONG("kyungdong", "경동택배"),
    DAESIN("daesin", "대신택배"),
    LOGEN("logen", "로젠택배"),
    HAPDONG("hapdong", "합동택배"),
    COUPANG("coupang", "쿠팡택배"),
    WOORI("woori", "우리택배");

    /** deliveryapi.co.kr API가 쓰는 courierCode 값. */
    private final String apiCode;
    private final String displayName;

    CourierCode(String apiCode, String displayName) {
        this.apiCode = apiCode;
        this.displayName = displayName;
    }

    /** 웹훅 payload의 courierCode(예: "cj")로 역매핑한다. 일치하는 게 없으면 null. */
    public static CourierCode fromApiCode(String apiCode) {
        for (CourierCode value : values()) {
            if (value.apiCode.equals(apiCode)) {
                return value;
            }
        }
        return null;
    }
}
