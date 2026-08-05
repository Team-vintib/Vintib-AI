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
     * 여러 판매자의 공개 상품 수(DRAFT 제외)를 한 번에 센다.
     *
     * <p>팔로워/팔로잉 목록, 홈 팔로잉 카드처럼 판매자가 여러 명인 응답에서 판매자마다
     * {@link #countBySeller_IdAndSaleStatusNot}을 부르면 N+1이 되므로 배치로 묶는다.
     */
    @Query("""
            SELECT p.seller.id AS sellerId, COUNT(p) AS count
            FROM Product p
            WHERE p.seller.id IN :sellerIds AND p.saleStatus <> :excludedStatus
            GROUP BY p.seller.id
            """)
    List<SellerProductCount> countBySellerIdsAndSaleStatusNot(
            @Param("sellerIds") Collection<Long> sellerIds, @Param("excludedStatus") SaleStatus excludedStatus);

    /** 여러 판매자의 상시 판매(ON_SALE) 상품을 최신순으로 가져온다(홈 팔로잉 콘텐츠) — {@code pageable}로 상위 N개만 캡. */
    List<Product> findBySeller_IdInAndSaleStatusOrderByCreatedAtDesc(
            Collection<Long> sellerIds, SaleStatus saleStatus, Pageable pageable);

    /** 마이페이지 판매 상품 관리(MY-002) — 본인 소유 상품은 DRAFT 등 비공개 상태까지 전부 보여준다. */
    Page<Product> findBySeller_IdOrderByCreatedAtDesc(Long sellerId, Pageable pageable);

    interface SellerProductCount {
        Long getSellerId();

        Long getCount();
    }

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
              AND (:hasSellerFilter = false OR p.seller.id = :sellerId)
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
            @Param("hasSellerFilter") boolean hasSellerFilter,
            @Param("sellerId") Long sellerId,
            Pageable pageable);
}
