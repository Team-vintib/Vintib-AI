package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductDefect;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductDefectRepository extends JpaRepository<ProductDefect, Long> {

    List<ProductDefect> findAllByProductIdOrderBySortOrderAsc(Long productId);
}
