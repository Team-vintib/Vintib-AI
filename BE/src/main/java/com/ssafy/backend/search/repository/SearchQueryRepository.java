package com.ssafy.backend.search.repository;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleType;
import java.util.Collection;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/**
 * 통합 검색(SEARCH-001/002)이 상품·라이브·회원을 읽는 <b>읽기 전용</b> 창구.
 *
 * <p>세 도메인을 한 인터페이스에 모은 이유는 검색이 "무엇을 어떻게 찾는지"를 한곳에서 보게
 * 하기 위해서다. 각 도메인 리포지토리에 검색 전용 메서드를 흩어 두면 정렬·필터 규칙이 갈린다.
 *
 * <p>{@code JpaRepository}가 아니라 {@code Repository}를 상속해 쓰기 메서드가 아예 노출되지
 * 않는다 — 검색은 무엇도 바꾸지 않는다.
 *
 * <p><b>키워드는 대소문자를 무시하고 부분 일치</b>다. 전문 검색 인덱스(GIN/pg_trgm)는 아직
 * 없으므로 데이터가 커지면 이 부분을 먼저 손봐야 한다.
 */
public interface SearchQueryRepository extends Repository<Product, Long> {

    /**
     * 상품 검색. 필터는 전부 선택이라 "걸지 여부" 불리언과 값을 쌍으로 받는다 —
     * {@code ProductRepository.findWithFilter}와 같은 방식이다(빈 컬렉션이 {@code IN ()}으로
     * 번역돼 질의가 깨지는 것을 막는다).
     *
     * <p>{@code DRAFT}는 판매자만 보는 임시 저장이라 검색에 절대 나오면 안 된다.
     */
    @Query("""
            SELECT p FROM Product p
            WHERE p.saleStatus <> com.ssafy.backend.product.entity.SaleStatus.DRAFT
              AND p.deletedAt IS NULL
              AND LOWER(p.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
              AND (:hasCategoryFilter = false OR p.categoryId IN :categoryIds)
              AND (:hasConditionFilter = false OR p.conditionGrade IN :conditionGrades)
              AND (:hasSaleTypeFilter = false OR p.saleType IN :saleTypes)
              AND (:hasMinPrice = false OR p.price >= :minPrice)
              AND (:hasMaxPrice = false OR p.price <= :maxPrice)
            """)
    Page<Product> searchProducts(
            @Param("keyword") String keyword,
            @Param("hasCategoryFilter") boolean hasCategoryFilter,
            @Param("categoryIds") Collection<Long> categoryIds,
            @Param("hasConditionFilter") boolean hasConditionFilter,
            @Param("conditionGrades") Collection<String> conditionGrades,
            @Param("hasSaleTypeFilter") boolean hasSaleTypeFilter,
            @Param("saleTypes") Collection<SaleType> saleTypes,
            @Param("hasMinPrice") boolean hasMinPrice,
            @Param("minPrice") Long minPrice,
            @Param("hasMaxPrice") boolean hasMaxPrice,
            @Param("maxPrice") Long maxPrice,
            Pageable pageable);

    /** 라이브 검색. 공개 상태(진행 중·예정)만 — 종료·취소된 방송은 들어갈 수 없다. */
    @Query("""
            SELECT l FROM Live l
            WHERE l.status IN :statuses
              AND LOWER(l.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
            """)
    Page<Live> searchLives(
            @Param("keyword") String keyword,
            @Param("statuses") Collection<LiveStatus> statuses,
            Pageable pageable);

    /**
     * 회원 검색. <b>닉네임으로만 찾는다</b> — 이메일·실명으로 찾게 두면 개인정보가 검색으로
     * 새어 나간다. 온보딩 전 회원은 닉네임이 없어 자연히 빠진다.
     */
    @Query("""
            SELECT m FROM Member m
            WHERE m.nickname IS NOT NULL
              AND LOWER(m.nickname) LIKE LOWER(CONCAT('%', :keyword, '%'))
            """)
    Page<Member> searchMembers(@Param("keyword") String keyword, Pageable pageable);
}
