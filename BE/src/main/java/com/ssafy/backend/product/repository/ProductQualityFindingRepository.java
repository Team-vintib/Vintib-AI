package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.ProductQualityFinding;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductQualityFindingRepository extends JpaRepository<ProductQualityFinding, Long> {

    List<ProductQualityFinding> findAllByProductIdOrderBySortOrderAsc(Long productId);

    // aiQualityAnalysis.images[].findings — 사진(앞/뒤)별로 나눠 담을 때 쓴다.
    List<ProductQualityFinding> findAllByProductIdAndPhotoRoleOrderBySortOrderAsc(
            Long productId, ProductImageRole photoRole);

    boolean existsByProductId(Long productId);

    // 수정(PATCH) 시 finding 목록을 전체 교체하기 전에 기존 것을 지운다(ProductDefectRepository와 같은 패턴).
    @Modifying
    @Query("delete from ProductQualityFinding f where f.product.id = :productId")
    void deleteAllByProductId(@Param("productId") Long productId);
}
