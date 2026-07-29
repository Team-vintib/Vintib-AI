package com.ssafy.backend.live.dto.request;

import org.springframework.data.domain.Sort;

/**
 * 공개 라이브 목록 정렬 기준.
 *
 * <p><b>모든 정렬의 마지막 기준은 {@code id DESC}다.</b> 동률일 때 순서가 흔들리면 페이지를
 * 넘길 때 같은 라이브가 두 번 보이거나 빠진다.
 *
 * <p>FE 요청서의 {@code VIEWERS_DESC}(시청자 수 순)는 아직 제공하지 않는다 — 현재 동시 시청자 수를
 * 집계하는 작업(-450)이 끝나야 값이 생긴다. 전부 0으로 내리면 정렬이 무의미하다.
 */
public enum LiveListSort {

    /**
     * 최신순. 진행 중인 방송이 먼저 오고(시작이 최근인 순), 그다음 예약 방송이 온다.
     *
     * <p>두 상태가 시각 컬럼을 따로 쓰기 때문에({@code startedAt} / {@code scheduledAt}) 한 컬럼으로는
     * 정렬되지 않는다. {@code NULLS LAST}를 명시하지 않으면 DB가 NULL을 어디에 둘지 정해버려서
     * 예약 방송이 진행 중 방송보다 위로 올라온다.
     */
    LATEST(Sort.by(
            new Sort.Order(Sort.Direction.DESC, "startedAt", Sort.NullHandling.NULLS_LAST),
            new Sort.Order(Sort.Direction.DESC, "scheduledAt", Sort.NullHandling.NULLS_LAST),
            Sort.Order.desc("id"))),

    /** 제목 오름차순. */
    TITLE_ASC(Sort.by(Sort.Order.asc("title"), Sort.Order.desc("id")));

    private final Sort sort;

    LiveListSort(Sort sort) {
        this.sort = sort;
    }

    public Sort toSort() {
        return sort;
    }
}