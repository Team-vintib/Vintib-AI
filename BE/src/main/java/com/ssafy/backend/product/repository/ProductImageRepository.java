package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductImage;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductImageRepository extends JpaRepository<ProductImage, Long> {

    List<ProductImage> findAllByProductIdOrderBySortOrderAsc(Long productId);

    int countByProductId(Long productId);

    // 대표 이미지는 상품당 1장만 유지한다 — 새로 대표로 지정되는 이미지를 저장/커밋하기
    // 전에 먼저 호출해 나머지를 내려야, 같은 트랜잭션 안에서 순서에 상관없이 일관된다.
    @Modifying
    @Query("update ProductImage i set i.primary = false where i.product.id = :productId")
    void clearPrimary(@Param("productId") Long productId);

    @Modifying
    @Query("update ProductImage i set i.primary = false where i.product.id = :productId and i.id <> :excludeId")
    void clearPrimaryExcept(@Param("productId") Long productId, @Param("excludeId") Long excludeId);
}