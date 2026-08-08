package com.ssafy.backend.product.config;

import java.util.Set;

/**
 * 데모 상품 시드(product-seed.sql) 중 "우선순위 높음"으로 확정된 상품의 id 목록.
 *
 * <p>product-seed.sql의 각 항목 주석에 번호가 남아있으면(예: {@code -- 2. Maison Kitsuné...})
 * 검수·확정된 상품이라는 뜻이고, 번호를 지웠으면 재검토 중이라는 뜻이다(사용자 컨벤션). 그
 * 구분은 SQL 주석에만 있고 DB 컬럼으로 저장되지 않아 런타임에 알 방법이 없다 — 그래서 이
 * 목록을 여기 하드코딩해 다른 데모 시더(주문·라이브)가 "우선순위 상품"을 우선 뽑을 때 쓴다.
 *
 * <p>product-seed.sql에서 번호를 더 지우거나 붙이면 이 목록도 같이 손으로 맞춰야 한다 —
 * 자동 동기화 장치가 없다. product-seed.sql은 한 상품당 정확히 파일 내 등장 순서대로
 * id 1..N을 받으므로(빈 테이블에 IDENTITY 컬럼), 여기 적힌 숫자는 "번호가 붙어있던 항목의
 * 파일 내 순번"과 정확히 같다.
 */
public final class DemoPriorityProducts {

    public static final Set<Long> IDS = Set.of(
            2L, 3L, 4L, 7L, 11L, 12L, 14L, 15L, 16L, 17L, 19L, 20L,
            26L, 27L, 29L, 30L, 31L, 32L, 33L, 34L, 35L, 36L, 37L, 38L, 39L, 40L,
            43L, 48L, 50L, 52L, 53L, 54L, 55L, 57L, 58L, 60L,
            62L, 63L, 64L, 65L, 66L,
            70L, 71L, 73L, 74L, 75L, 76L, 77L, 78L, 79L, 80L, 81L, 82L,
            87L, 88L, 90L, 92L, 95L, 96L, 97L, 98L,
            101L);

    private DemoPriorityProducts() {
    }
}
