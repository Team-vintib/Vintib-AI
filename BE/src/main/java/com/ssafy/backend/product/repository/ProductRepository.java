package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductRepository extends JpaRepository<Product, Long> {

    Page<Product> findBySaleStatusNotIn(List<SaleStatus> excludedStatuses, Pageable pageable);

    /** 카테고리로 상품을 찾는다. 라이브 목록의 카테고리 필터가 쓴다. */
    List<Product> findByCategoryIdIn(Collection<Long> categoryIds);
}