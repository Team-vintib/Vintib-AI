package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductImage;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductImageRepository extends JpaRepository<ProductImage, Long> {

    List<ProductImage> findAllByProductIdOrderBySortOrderAsc(Long productId);

    int countByProductId(Long productId);
}