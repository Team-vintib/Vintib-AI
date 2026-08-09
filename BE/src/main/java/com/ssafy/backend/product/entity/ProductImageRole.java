package com.ssafy.backend.product.entity;

/**
 * 상품 이미지의 용도. {@code FRONT}/{@code BACK}은 AI 품질 검수의 앞/뒤 사진(하자 검증용)
 * 이자 {@code image_index} 0/1에 대응한다.
 * {@code ADDITIONAL}은 그 외 나머지 참고 사진이다.
 */
public enum ProductImageRole {
    FRONT,
    BACK,
    ADDITIONAL
}
