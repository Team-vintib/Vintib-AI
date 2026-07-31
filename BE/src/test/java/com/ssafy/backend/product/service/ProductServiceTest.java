package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductDefect;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductDefectRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    private static final Long SELLER_ID = 1L;
    private static final Long CATEGORY_ID = 10L;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductImageService productImageService;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private ProductDefectRepository productDefectRepository;

    @Mock
    private Member seller;

    private ProductService productService;

    @BeforeEach
    void setUp() {
        productService = new ProductService(
                productRepository, memberRepository, productImageService, categoryRepository, productDefectRepository);
    }

    @Test
    void 상품_기본_정보를_저장하면_saleType_없이_DRAFT_상태로_생성된다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, 2L, "A급", "M", null, null, null, null);

        ProductResponse response = productService.createProduct(SELLER_ID, request);

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.DRAFT);
        assertThat(response.saleType()).isNull();
        assertThat(response.sellerId()).isEqualTo(SELLER_ID);
        assertThat(response.title()).isEqualTo("빈티지 자켓");
        assertThat(response.categoryId()).isEqualTo(CATEGORY_ID);
    }

    @Test
    void 색상_소재_실측_하자를_포함해_상품을_등록할_수_있다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓",
                "설명",
                CATEGORY_ID,
                2L,
                "A급",
                "M",
                "블랙",
                "데님",
                Map.of("총장", 70),
                List.of("소매 끝 실밥 풀림", "안감 얼룩"));

        ProductResponse response = productService.createProduct(SELLER_ID, request);

        assertThat(response.title()).isEqualTo("빈티지 자켓");

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<ProductDefect>> captor = ArgumentCaptor.forClass(List.class);
        verify(productDefectRepository).saveAll(captor.capture());
        List<ProductDefect> saved = captor.getValue();
        assertThat(saved).hasSize(2);
        assertThat(saved.get(0).getContent()).isEqualTo("소매 끝 실밥 풀림");
        assertThat(saved.get(0).getSortOrder()).isEqualTo((short) 0);
        assertThat(saved.get(1).getContent()).isEqualTo("안감 얼룩");
        assertThat(saved.get(1).getSortOrder()).isEqualTo((short) 1);
    }

    @Test
    void 하자_목록이_없으면_defect_저장을_호출하지_않는다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, 2L, "A급", "M", null, null, null, null);

        productService.createProduct(SELLER_ID, request);

        verify(productDefectRepository, never()).saveAll(any());
    }

    @Test
    void 존재하지_않는_판매자면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.empty());

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", null, CATEGORY_ID, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_카테고리면_상품을_등록할_수_없다() {
        // @NotNull 은 "값이 있는지"만 본다. 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나가므로
        // 서비스에서 존재를 확인한다.
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(false);

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, 2L, "A급", "M", null, null, null, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CATEGORY_NOT_FOUND);
        verify(productRepository, never()).save(any());
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
    void DRAFT_상품을_경매_예정으로_등록한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response = productService.scheduleAuction(SELLER_ID, 1L);

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.AUCTION_SCHEDULED);
        assertThat(response.saleType()).isEqualTo(SaleType.AUCTION);
        assertThat(response.price()).isNull();
    }

    @Test
    void ON_SALE_상품을_경매_예정으로_전환한다() {
        // 상시 판매 상품의 경매 전환(PROD-004) — DRAFT에서 경매 예정으로 등록하는 것과 같은 메서드를 쓴다.
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response = productService.scheduleAuction(SELLER_ID, 1L);

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.AUCTION_SCHEDULED);
        assertThat(response.saleType()).isEqualTo(SaleType.AUCTION);
        assertThat(response.price()).isNull();
    }

    @Test
    void DRAFT_또는_ON_SALE이_아니면_경매_등록시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.SOLD);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productService.scheduleAuction(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
    }

    @Test
    void 본인이_아니면_경매_등록시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productService.scheduleAuction(2L, 1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_PRODUCT_OWNER);
    }

    @Test
    void 존재하지_않는_상품이면_경매_등록시_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productService.scheduleAuction(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 미낙찰_상품을_상시_판매로_전환한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.AUCTION_SCHEDULED);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response =
                productService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(30000L));

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.ON_SALE);
        assertThat(response.saleType()).isEqualTo(SaleType.DIRECT_SALE);
        assertThat(response.price()).isEqualTo(30000L);
    }

    @Test
    void DRAFT_또는_AUCTION_SCHEDULED가_아니면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.SOLD);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() ->
                productService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(60000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
    }

    @Test
    void 상품_목록_조회시_DRAFT_상태는_제외하고_조회한다() {
        Product onSale = Product.builder().seller(seller).title("상시 판매 상품").build();
        onSale.registerDirectSale(10000L);
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findBySaleStatusNotIn(any(), any()))
                .thenReturn(new PageImpl<>(List.of(onSale), pageable, 1));

        PageResponse<ProductResponse> response = productService.getProductList(pageable);

        verify(productRepository).findBySaleStatusNotIn(eq(List.of(SaleStatus.DRAFT)), any(Pageable.class));
        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).saleStatus()).isEqualTo(SaleStatus.ON_SALE);
    }

    @Test
    void 상품_목록_조회시_페이지네이션_정보를_반환한다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        Pageable pageable = PageRequest.of(0, 2);
        when(productRepository.findBySaleStatusNotIn(any(), any()))
                .thenReturn(new PageImpl<>(List.of(product, product), pageable, 5));

        PageResponse<ProductResponse> response = productService.getProductList(pageable);

        assertThat(response.page()).isEqualTo(0);
        assertThat(response.size()).isEqualTo(2);
        assertThat(response.totalElements()).isEqualTo(5);
        assertThat(response.totalPages()).isEqualTo(3);
        assertThat(response.hasNext()).isTrue();
    }

    @Test
    void 상품_목록이_비어있으면_빈_배열을_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findBySaleStatusNotIn(any(), any()))
                .thenReturn(new PageImpl<>(List.of(), pageable, 0));

        PageResponse<ProductResponse> response = productService.getProductList(pageable);

        assertThat(response.content()).isEmpty();
        assertThat(response.totalElements()).isZero();
        assertThat(response.hasNext()).isFalse();
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
    void DRAFT_상품은_본인만_조회할_수_있다() {
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

    @Test
    void 본인_상품을_부분_수정하면_반영된_필드만_바뀐다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder()
                .seller(seller)
                .title("빈티지 자켓")
                .description("기존 설명")
                .sizeLabel("M")
                .build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest("수정된 제목", null, null, null, null, null);
        ProductResponse response = productService.updateProduct(SELLER_ID, 1L, request);

        assertThat(response.title()).isEqualTo("수정된 제목");
        assertThat(response.description()).isEqualTo("기존 설명");
        assertThat(response.sizeLabel()).isEqualTo("M");
    }

    @Test
    void 본인이_아니면_수정시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest("수정된 제목", null, null, null, null, null);

        assertThatThrownBy(() -> productService.updateProduct(2L, 1L, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 수정_불가_상태면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.SOLD);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest("수정된 제목", null, null, null, null, null);

        assertThatThrownBy(() -> productService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인_상품을_삭제하면_이후_상세조회가_404가_된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        productService.deleteProduct(SELLER_ID, 1L);

        assertThat(product.isDeleted()).isTrue();
        assertThatThrownBy(() -> productService.getProductDetail(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인이_아니면_삭제시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productService.deleteProduct(2L, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 삭제_불가_상태면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.AUCTION_IN_PROGRESS);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productService.deleteProduct(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_카테고리로는_수정할_수_없다() {
        // 등록과 같은 규칙이다 — category_id 에 FK 가 걸려 있어 그냥 통과시키면 500 이 된다.
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).categoryId(CATEGORY_ID).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(false);

        ProductUpdateRequest request = new ProductUpdateRequest(null, null, CATEGORY_ID, null, null, null);

        assertThatThrownBy(() -> productService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CATEGORY_NOT_FOUND);
    }
}