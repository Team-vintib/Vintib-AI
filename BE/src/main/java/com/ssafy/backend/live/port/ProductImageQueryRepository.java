package com.ssafy.backend.live.port;

import com.ssafy.backend.product.entity.ProductImage;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/**
 * 편성 상품들의 이미지를 한 번에 읽는다. {@link ProductQueryAdapter} 전용이다.
 *
 * <p><b>왜 상품 도메인의 {@code ProductImageRepository}를 쓰지 않는가.</b> 거기에는 상품 하나씩
 * 읽는 메서드만 있어서, 편성 상품 수만큼 쿼리가 나간다. 필요한 메서드를 그쪽에 추가하면 서윤
 * 영역의 파일을 고치게 되므로, <b>읽기 전용 조회를 이 패키지에 따로 둔다.</b>
 * 같은 엔티티를 두 리포지토리가 읽는 것은 문제가 없다 — 쓰기는 여전히 상품 도메인만 한다.
 *
 * <p>{@code Repository} 를 직접 상속해 <b>조회 메서드 하나만</b> 노출한다. {@code JpaRepository}
 * 를 상속하면 {@code save}·{@code delete} 까지 열려서 격리한 의미가 없어진다.
 */
interface ProductImageQueryRepository extends Repository<ProductImage, Long> {

    /**
     * 여러 상품의 이미지를 정렬 순서대로.
     *
     * <p>대표 이미지({@code primary})를 먼저 오게 정렬한다 — 지정된 것이 없으면 {@code sortOrder}
     * 가 가장 앞선 이미지가 대표 역할을 한다.
     */
    @Query("""
            SELECT pi FROM ProductImage pi
            WHERE pi.product.id IN :productIds
            ORDER BY pi.product.id ASC, pi.primary DESC, pi.sortOrder ASC
            """)
    List<ProductImage> findAllByProductIds(@Param("productIds") Collection<Long> productIds);
}
