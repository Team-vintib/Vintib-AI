package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.ProductDefect;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductDefectRepository extends JpaRepository<ProductDefect, Long> {

    List<ProductDefect> findAllByProductIdOrderBySortOrderAsc(Long productId);

    // 수정 시 하자 목록을 전체 교체하기 전에 기존 것을 지운다.
    @Modifying
    @Query("delete from ProductDefect d where d.product.id = :productId")
    void deleteAllByProductId(@Param("productId") Long productId);
}
