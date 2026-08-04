package com.ssafy.backend.live.port;

import com.ssafy.backend.product.entity.ProductDefect;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/**
 * 편성 상품들의 하자 목록을 한 번에 읽는다. {@link ProductQueryAdapter} 전용이다.
 *
 * <p>{@code ProductDefectRepository}(상품 도메인)에는 상품 하나씩 읽는 메서드만 있어
 * {@link ProductImageQueryRepository}와 같은 이유로 읽기 전용 조회를 이 패키지에 따로 둔다.
 */
interface ProductDefectQueryRepository extends Repository<ProductDefect, Long> {

    @Query("""
            SELECT d FROM ProductDefect d
            WHERE d.product.id IN :productIds
            ORDER BY d.product.id ASC, d.sortOrder ASC
            """)
    List<ProductDefect> findAllByProductIds(@Param("productIds") Collection<Long> productIds);
}
