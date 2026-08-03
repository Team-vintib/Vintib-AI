package com.ssafy.backend.auction.port;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/**
 * {@link ProductCommandPort} 전용 — 상품의 판매 상태만 바꾸는 좁은 리포지토리.
 *
 * <p><b>{@code ProductRepository}에 메서드를 더하지 않는 이유</b>는 병합 충돌이다. 상품
 * 리포지토리는 서윤 담당 파일이고, 경매 사정으로 계속 고치면 서로 부딪힌다.
 *
 * <p><b>엔티티 메서드가 아니라 벌크 UPDATE 인 이유.</b> 상태를 바꾸려면 {@code Product}에
 * 메서드를 하나 더해야 하는데 그것도 서윤 파일이다. 여기서 바꾸는 것은 {@code sale_status}
 * 한 컬럼뿐이고 다른 필드와 얽힌 불변식이 없어, 한 문장 UPDATE 로 끝내는 편이 안전하다.
 *
 * <p>{@code flushAutomatically}·{@code clearAutomatically}를 켠다 — 벌크 UPDATE 는 영속성
 * 컨텍스트를 우회하므로, 같은 트랜잭션에서 이 상품을 이미 읽었다면 옛 상태가 남는다.
 */
public interface ProductSaleStatusRepository extends Repository<Product, Long> {

    /**
     * 판매 상태를 바꾼다. <b>이미 그 상태면 아무 행도 바뀌지 않는다</b>(재시도해도 안전하다).
     *
     * @return 바뀐 행 수(0 또는 1)
     */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("""
            UPDATE Product p SET p.saleStatus = :status
            WHERE p.id = :productId AND p.saleStatus <> :status
            """)
    int updateSaleStatus(@Param("productId") Long productId, @Param("status") SaleStatus status);
}
