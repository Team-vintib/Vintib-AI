package com.ssafy.backend.home.repository;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.Repository;

/**
 * 홈 화면이 상품을 읽기 위한 <b>읽기 전용</b> 리포지토리.
 *
 * <p><b>{@code ProductRepository}에 메서드를 더하지 않고 따로 두는 이유.</b> 상품 리포지토리는
 * 서윤 담당 파일이라 홈 화면 사정으로 계속 고치면 병합 충돌이 잦아진다. 홈이 필요한 질의만
 * 여기 모아 두면 상품 도메인 쪽 변경과 서로 부딪히지 않는다.
 *
 * <p>{@code JpaRepository}가 아니라 {@code Repository}를 상속한다 — {@code save}·{@code delete}가
 * 노출되지 않아 <b>홈에서 상품을 쓰는 일이 애초에 불가능</b>하다. 같은 이유로
 * {@code live/port/ProductImageQueryRepository}도 이 방식이다.
 */
public interface HomeProductQueryRepository extends Repository<Product, Long> {

    /** 특정 판매 상태의 상품을 최신 등록순으로. 홈 "정찰제"·"경매 예정" 섹션이 쓴다. */
    List<Product> findBySaleStatusOrderByCreatedAtDesc(SaleStatus saleStatus, Pageable pageable);

    /**
     * 카테고리 탭 섹션(HOME-001)용 — 주어진 카테고리들에 속한 판매 중 상품.
     *
     * <p>탭마다 따로 질의하면 탭 수만큼 왕복하므로 <b>한 번에 긁어 와서 메모리에서 나눈다.</b>
     * 대분류 탭이라도 상품은 소분류에 달려 있어, 호출부가 하위 카테고리 ID까지 펼쳐서 넘긴다.
     */
    List<Product> findByCategoryIdInAndSaleStatusOrderByCreatedAtDesc(
            Collection<Long> categoryIds, SaleStatus saleStatus, Pageable pageable);
}
