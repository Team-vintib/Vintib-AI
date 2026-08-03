package com.ssafy.backend.search.dto.request;

/**
 * 검색 대상 탭(SEARCH-001). {@code ALL}이면 세 섹션을 함께 채우고, 나머지는 해당 섹션만 채우고
 * 다른 섹션은 <b>{@code null}</b>로 내린다 — 빈 배열은 "찾았지만 결과 0건"이라는 뜻이라
 * "조회하지 않았다"와 구분해야 한다.
 */
public enum SearchType {
    ALL,
    PRODUCT,
    LIVE,
    USER;

    public boolean includes(SearchType target) {
        return this == ALL || this == target;
    }
}
