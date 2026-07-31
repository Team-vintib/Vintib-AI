package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductRepository extends JpaRepository<Product, Long> {

    Page<Product> findBySaleStatusNotIn(List<SaleStatus> excludedStatuses, Pageable pageable);

    /** 카테고리로 상품을 찾는다. 라이브 목록의 카테고리 필터가 쓴다. */
    List<Product> findByCategoryIdIn(Collection<Long> categoryIds);

    /** 판매자의 공개 상품 수(DRAFT 제외) — 상품 상세의 판매자 통계에 쓴다. */
    long countBySeller_IdAndSaleStatusNot(Long sellerId, SaleStatus excludedStatus);

    /**
     * 선택적 필터·정렬을 지원하는 상품 목록 조회 (PROD-008).
     *
     * <p>각 boolean 플래그가 false 이면 대응하는 WHERE 절을 건너뛴다
     * — LiveRepository.findPublicLives 가 쓰는 패턴과 동일하다.
     * DRAFT 상태는 항상 제외한다.
     *
     * <p>가격 필터(minPrice/maxPrice)는 price 가 null 인 경매 예정 상품에는
     * 실질적으로 작동하지 않는다. 경매 예정은 가격이 없으므로 hasMinPriceFilter=true 이면
     * JPQL 의 (:flag = false OR p.price >= :min) 조건에서 항상 false 가 되어 제외된다.
     * FE 가 가격 필터를 쓸 때 경매 예정 상품이 자동 제외되는 것은 의도된 동작이다.
     */
    @Query("""
            SELECT p FROM Product p
            WHERE p.saleStatus <> 'DRAFT'
              AND (:hasCategoryFilter = false OR p.categoryId IN :categoryIds)
              AND (:hasConditionFilter = false OR p.conditionGrade IN :conditionGrades)
              AND (:hasSaleTypeFilter = false OR p.saleType = :saleType)
              AND (:hasMinPrice = false OR p.price >= :minPrice)
              AND (:hasMaxPrice = false OR p.price <= :maxPrice)
            """)
    Page<Product> findWithFilter(
            @Param("hasCategoryFilter") boolean hasCategoryFilter,
            @Param("categoryIds") List<Long> categoryIds,
            @Param("hasConditionFilter") boolean hasConditionFilter,
            @Param("conditionGrades") List<String> conditionGrades,
            @Param("hasSaleTypeFilter") boolean hasSaleTypeFilter,
            @Param("saleType") SaleType saleType,
            @Param("hasMinPrice") boolean hasMinPrice,
            @Param("minPrice") Long minPrice,
            @Param("hasMaxPrice") boolean hasMaxPrice,
            @Param("maxPrice") Long maxPrice,
            Pageable pageable);
}
