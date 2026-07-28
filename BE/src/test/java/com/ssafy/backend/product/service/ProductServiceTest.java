package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    private static final Long SELLER_ID = 1L;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductImageService productImageService;

    @Mock
    private Member seller;

    private ProductService productService;

    @BeforeEach
    void setUp() {
        productService = new ProductService(productRepository, memberRepository, productImageService);
    }

    @Test
    void 상품_기본_정보를_저장하면_saleType_없이_DRAFT_상태로_생성된다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request =
                new ProductCreateRequest("빈티지 자켓", "설명", 1L, 2L, "A급", "M");

        ProductResponse response = productService.createProduct(SELLER_ID, request);

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.DRAFT);
        assertThat(response.saleType()).isNull();
        assertThat(response.sellerId()).isEqualTo(SELLER_ID);
        assertThat(response.title()).isEqualTo("빈티지 자켓");
    }

    @Test
    void 존재하지_않는_판매자면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.empty());

        ProductCreateRequest request = new ProductCreateRequest("빈티지 자켓", null, null, null, null, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void DRAFT_상품에_가격을_설정하면_상시_판매_상태로_전환된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response =
                productService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(50000L));

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.ON_SALE);
        assertThat(response.saleType()).isEqualTo(SaleType.DIRECT_SALE);
        assertThat(response.price()).isEqualTo(50000L);
    }

    @Test
    void 존재하지_않는_상품이면_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() ->
                productService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(50000L)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인이_등록한_상품이_아니면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        Long otherSellerId = 2L;
        assertThatThrownBy(() ->
                productService.registerDirectSale(otherSellerId, 1L, new ProductStatusUpdateRequest(50000L)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void DRAFT_상태가_아니면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() ->
                productService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(60000L)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 공개_상태_상품은_비로그인_또는_타인도_조회할_수_있다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse loggedOutResponse = productService.getProductDetail(null, 1L);
        ProductDetailResponse otherViewerResponse = productService.getProductDetail(2L, 1L);

        assertThat(loggedOutResponse.saleStatus()).isEqualTo(SaleStatus.ON_SALE);
        assertThat(loggedOutResponse.sellerNickname()).isEqualTo("판매자");
        assertThat(otherViewerResponse.id()).isEqualTo(loggedOutResponse.id());
    }

    @Test
    void DRAFT_또는_PRIVATE_상품은_본인만_조회할_수_있다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse ownerResponse = productService.getProductDetail(SELLER_ID, 1L);

        assertThat(ownerResponse.saleStatus()).isEqualTo(SaleStatus.DRAFT);
        assertThatThrownBy(() -> productService.getProductDetail(2L, 1L))
                .isInstanceOf(CustomException.class);
        assertThatThrownBy(() -> productService.getProductDetail(null, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_상품을_조회하면_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productService.getProductDetail(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }
}
