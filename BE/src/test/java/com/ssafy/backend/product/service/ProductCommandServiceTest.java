package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.repository.CategoryRepository;
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

@ExtendWith(MockitoExtension.class)
class ProductCommandServiceTest {

    private static final Long SELLER_ID = 1L;
    private static final Long CATEGORY_ID = 10L;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private Member seller;

    private ProductCommandService productCommandService;

    @BeforeEach
    void setUp() {
        productCommandService = new ProductCommandService(productRepository, memberRepository, categoryRepository);
    }

    @Test
    void 상품_기본_정보를_저장하면_saleType_없이_DRAFT_상태로_생성된다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, false, null);

        ProductResponse response = productCommandService.createProduct(SELLER_ID, request);

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
                "리바이스",
                "A급",
                null,
                "M",
                "블랙",
                "데님",
                Map.of("총장", 70),
                List.of("소매 끝 실밥 풀림", "안감 얼룩"),
                false,
                null);

        ProductResponse response = productCommandService.createProduct(SELLER_ID, request);

        assertThat(response.title()).isEqualTo("빈티지 자켓");

        ArgumentCaptor<Product> captor = ArgumentCaptor.forClass(Product.class);
        verify(productRepository).save(captor.capture());
        assertThat(captor.getValue().getDefects())
                .containsExactly("소매 끝 실밥 풀림", "안감 얼룩");
    }

    @Test
    void 하자_목록이_없으면_defects는_null로_저장된다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, false, null);

        ArgumentCaptor<Product> captor = ArgumentCaptor.forClass(Product.class);
        productCommandService.createProduct(SELLER_ID, request);

        verify(productRepository).save(captor.capture());
        assertThat(captor.getValue().getDefects()).isNull();
    }

    @Test
    void 존재하지_않는_판매자면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.empty());

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", null, CATEGORY_ID, null, null, null, null, null, null, null, null, false, null);

        assertThatThrownBy(() -> productCommandService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_카테고리면_상품을_등록할_수_없다() {
        // @NotNull 은 "값이 있는지"만 본다. 없는 ID 를 그대로 넣으면 FK 위반이 500 으로 새어 나가므로
        // 서비스에서 존재를 확인한다.
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(false);

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, false, null);

        assertThatThrownBy(() -> productCommandService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CATEGORY_NOT_FOUND);
        verify(productRepository, never()).save(any());
    }

    @Test
    void AI_착용컷을_활성화하면서_모델_성별을_지정하지_않으면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, true, null);

        assertThatThrownBy(() -> productCommandService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AI_MODEL_GENDER_REQUIRED);
        verify(productRepository, never()).save(any());
    }

    @Test
    void AI_착용컷_활성화와_모델_성별을_함께_저장한다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null,
                true, com.ssafy.backend.product.entity.AiModelGender.FEMALE);

        ArgumentCaptor<Product> captor = ArgumentCaptor.forClass(Product.class);
        productCommandService.createProduct(SELLER_ID, request);

        verify(productRepository).save(captor.capture());
        assertThat(captor.getValue().isAiModelEnabled()).isTrue();
        assertThat(captor.getValue().getAiModelGender())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelGender.FEMALE);
    }

    @Test
    void DRAFT_상품에_가격을_설정하면_상시_판매_상태로_전환된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response =
                productCommandService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(50000L));

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.ON_SALE);
        assertThat(response.saleType()).isEqualTo(SaleType.DIRECT_SALE);
        assertThat(response.price()).isEqualTo(50000L);
    }

    @Test
    void 존재하지_않는_상품이면_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() ->
                productCommandService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(50000L)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인이_등록한_상품이_아니면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        Long otherSellerId = 2L;
        assertThatThrownBy(() ->
                productCommandService.registerDirectSale(otherSellerId, 1L, new ProductStatusUpdateRequest(50000L)))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void DRAFT_상품을_경매_예정으로_등록한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response = productCommandService.scheduleAuction(SELLER_ID, 1L);

        assertThat(response.saleStatus()).isEqualTo(SaleStatus.AUCTION_SCHEDULED);
        assertThat(response.saleType()).isEqualTo(SaleType.AUCTION);
        assertThat(response.price()).isNull();
    }

    @Test
    void ON_SALE_상품을_경매_예정으로_전환한다() {
        // 정찰제 상품의 경매 전환(PROD-004) — DRAFT에서 경매 예정으로 등록하는 것과 같은 메서드를 쓴다.
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductResponse response = productCommandService.scheduleAuction(SELLER_ID, 1L);

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

        assertThatThrownBy(() -> productCommandService.scheduleAuction(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
    }

    @Test
    void 본인이_아니면_경매_등록시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productCommandService.scheduleAuction(2L, 1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_PRODUCT_OWNER);
    }

    @Test
    void 존재하지_않는_상품이면_경매_등록시_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productCommandService.scheduleAuction(SELLER_ID, 1L))
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
                productCommandService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(30000L));

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
                productCommandService.registerDirectSale(SELLER_ID, 1L, new ProductStatusUpdateRequest(60000L)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
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

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);
        ProductResponse response = productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(response.title()).isEqualTo("수정된 제목");
        assertThat(response.description()).isEqualTo("기존 설명");
        assertThat(response.sizeLabel()).isEqualTo("M");
    }

    @Test
    void 본인_상품을_수정하면_색상_소재_실측이_반영된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, "블랙", "데님", Map.of("총장", 70), null, null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getColor()).isEqualTo("블랙");
        assertThat(product.getMaterial()).isEqualTo("데님");
        assertThat(product.getMeasurements()).isEqualTo(Map.of("총장", 70));
    }

    @Test
    void 본인_상품을_수정하면_matchKey가_반영된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null, null, null, "1:501-리바이스:97", null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getMatchKey()).isEqualTo("1:501-리바이스:97");
    }

    @Test
    void matchKey가_null이면_기존_값을_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "matchKey", "1:501-리바이스:97");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getMatchKey()).isEqualTo("1:501-리바이스:97");
    }

    @Test
    void 하자_목록을_보내면_전체_교체된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "defects", List.of("기존 하자"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, List.of("얼룩"), null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getDefects()).containsExactly("얼룩");
    }

    @Test
    void 하자를_빈_배열로_보내면_기존_하자를_전부_비운다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "defects", List.of("기존 하자"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, List.of(), null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getDefects()).isEmpty();
    }

    @Test
    void 하자가_null이면_기존_하자를_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "defects", List.of("기존 하자"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getDefects()).containsExactly("기존 하자");
    }

    @Test
    void 제외_key_목록을_보내면_기존_것을_전체_교체한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "excludedQualityFindingKeys", List.of("stain_0_5_1"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null,
                List.of("hole_tear_0_2_1"), null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getExcludedQualityFindingKeys()).containsExactly("hole_tear_0_2_1");
    }

    @Test
    void 제외_key_목록이_null이면_기존_값을_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "excludedQualityFindingKeys", List.of("stain_0_5_1"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getExcludedQualityFindingKeys()).containsExactly("stain_0_5_1");
    }

    @Test
    void 제외_key_목록을_빈_배열로_보내면_기존_제외_목록을_전부_해제한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "excludedQualityFindingKeys", List.of("stain_0_5_1"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null, List.of(), null, null, null);
        productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getExcludedQualityFindingKeys()).isEmpty();
    }

    @Test
    void 본인이_아니면_수정시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productCommandService.updateProduct(2L, 1L, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 수정_불가_상태면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.SOLD);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productCommandService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 본인_상품을_삭제하면_소프트_삭제된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        productCommandService.deleteProduct(SELLER_ID, 1L);

        assertThat(product.isDeleted()).isTrue();
    }

    @Test
    void 본인이_아니면_삭제시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productCommandService.deleteProduct(2L, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 삭제_불가_상태면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.AUCTION_IN_PROGRESS);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productCommandService.deleteProduct(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_카테고리로는_수정할_수_없다() {
        // 등록과 같은 규칙이다 — category_id 에 FK 가 걸려 있어 그냥 통과시키면 500 이 된다.
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).categoryId(CATEGORY_ID).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(false);

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, CATEGORY_ID, null, null, null, null, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productCommandService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CATEGORY_NOT_FOUND);
    }

    @Test
    void 상시_판매_상품은_가격을_수정할_수_있다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50_000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null, null, 45_000L, null, null);
        ProductResponse response = productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(response.price()).isEqualTo(45_000L);
    }

    @Test
    void 경매_상품은_가격을_수정할_수_없다() {
        // price가 요청에 담기면 saleType 무관하게 그냥 통과시키는 게 아니라 400으로 막는다 —
        // 경매 상품의 price는 항상 null이고 시작가는 Auction 엔티티가 별도로 갖는다.
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.scheduleAuction();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null, null, 45_000L, null, null);

        assertThatThrownBy(() -> productCommandService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
    }

    @Test
    void 가격이_없으면_기존_가격을_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50_000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                "수정된 제목", null, null, null, null, null, null, null, null, null, null, null, null, null);
        ProductResponse response = productCommandService.updateProduct(SELLER_ID, 1L, request);

        assertThat(response.price()).isEqualTo(50_000L);
    }
}
