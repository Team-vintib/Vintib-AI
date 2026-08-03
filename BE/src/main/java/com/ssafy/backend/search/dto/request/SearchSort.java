package com.ssafy.backend.search.dto.request;

import org.springframework.data.domain.Sort;

/**
 * 검색 결과 정렬(SEARCH-002).
 *
 * <p><b>가격 정렬은 상품에만 적용된다</b> — 라이브·회원에는 가격이 없어 최신순으로 둔다.
 * 관련도순은 전문 검색 인덱스가 있어야 의미가 있어 지금은 제공하지 않는다(부분 일치라
 * 점수를 매길 근거가 없다).
 */
public enum SearchSort {

    /** 기본값. 최근 등록순. */
    LATEST,
    PRICE_ASC,
    PRICE_DESC;

    public Sort toProductSort() {
        return switch (this) {
            case PRICE_ASC -> Sort.by(Sort.Direction.ASC, "price");
            case PRICE_DESC -> Sort.by(Sort.Direction.DESC, "price");
            case LATEST -> Sort.by(Sort.Direction.DESC, "createdAt");
        };
    }
}
