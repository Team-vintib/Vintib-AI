package com.ssafy.backend.live.dto.request;

import org.springframework.data.domain.Sort;

/**
 * 공개 라이브 목록 정렬 기준.
 *
 * <p><b>모든 정렬의 마지막 기준은 {@code id DESC}다.</b> 동률일 때 순서가 흔들리면 페이지를
 * 넘길 때 같은 라이브가 두 번 보이거나 빠진다.
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
    TITLE_ASC(Sort.by(Sort.Order.asc("title"), Sort.Order.desc("id"))),

    /**
     * 시청자 수 많은 순(-450).
     *
     * <p><b>이 정렬만 SQL 로 처리되지 않는다.</b> 현재 시청자 수는 Redis 에만 있는 휘발성 값이라
     * {@code ORDER BY} 로 걸 컬럼이 없다. 그래서 {@code LiveService} 가 후보를 한 번에 읽어
     * 메모리에서 정렬하고 페이지를 잘라낸다 — 여기서 돌려주는 {@link Sort} 는 그 후보를 뽑을 때
     * 쓰는 <b>안정적인 기준 순서</b>일 뿐, 최종 정렬 기준이 아니다.
     *
     * <p>같은 값을 {@code live} 테이블에도 저장하면 SQL 정렬이 가능해지지만, 시청자가 들고 날
     * 때마다 DB write 가 발생한다. 목록에 나올 수 있는 방송(예정·진행 중)의 수가 훨씬 작으므로
     * 메모리 정렬이 싸다.
     */
    VIEWERS_DESC(Sort.by(Sort.Order.desc("id")));

    private final Sort sort;

    LiveListSort(Sort sort) {
        this.sort = sort;
    }

    public Sort toSort() {
        return sort;
    }

    /** 정렬을 DB 가 아니라 메모리에서 해야 하는지. */
    public boolean isInMemory() {
        return this == VIEWERS_DESC;
    }
}
