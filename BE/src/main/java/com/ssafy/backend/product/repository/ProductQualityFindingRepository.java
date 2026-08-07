package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.ProductQualityFinding;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductQualityFindingRepository extends JpaRepository<ProductQualityFinding, Long> {

    List<ProductQualityFinding> findAllByProductIdOrderBySortOrderAsc(Long productId);

    // aiQualityAnalysis.images[].findings — 사진(앞/뒤)별로 나눠 담을 때 쓴다.
    List<ProductQualityFinding> findAllByProductIdAndPhotoRoleOrderBySortOrderAsc(
            Long productId, ProductImageRole photoRole);

    boolean existsByProductId(Long productId);
}
