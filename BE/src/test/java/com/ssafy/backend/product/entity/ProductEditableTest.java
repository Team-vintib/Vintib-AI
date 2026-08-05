package com.ssafy.backend.product.entity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * 상품 내용을 고칠 수 있는 상태인지({@link Product#isEditable()}).
 *
 * <p>유찰된 상품이 재편집 가능해야 한다는 요구(FE 요청 007)에서 나온 규칙이라, 어느 상태가
 * 열리고 어느 상태가 닫히는지를 못박아 둔다.
 */
class ProductEditableTest {

    private Product 등록된_상품() {
        return Product.builder().title("빈티지 자켓").build();
    }

    @Test
    void 작성_중_상품은_수정할_수_있다() {
        assertThat(등록된_상품().isEditable()).isTrue();
    }

    @Test
    void 상시_판매_상품은_수정할_수_있다() {
        Product product = 등록된_상품();
        product.registerDirectSale(50_000L);

        assertThat(product.isEditable()).isTrue();
    }

    @Test
    void 경매_예정_상품은_수정할_수_있다() {
        // 유찰된 상품이 이 상태로 돌아온다 — "안 팔렸으니 설명 고쳐서 다시 걸자"가 막히면 안 된다.
        Product product = 등록된_상품();
        product.scheduleAuction();

        assertThat(product.isEditable()).isTrue();
    }

    @Test
    void 경매가_진행_중이면_수정할_수_없다() {
        // 입찰이 붙는 도중에 상품 정보가 바뀌면 입찰자가 보고 판단한 것과 달라진다.
        // 이 전이는 엔티티 메서드가 아니라 경매 쪽 벌크 UPDATE(ProductSaleStatusRepository)로
        // 일어나므로, 여기서는 상태를 직접 세워 규칙만 확인한다.
        Product product = 등록된_상품();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.AUCTION_IN_PROGRESS);

        assertThat(product.isEditable()).isFalse();
    }

    @Test
    void 팔린_상품은_수정할_수_없다() {
        Product product = 등록된_상품();
        product.markSold();

        assertThat(product.isEditable()).isFalse();
    }
}
