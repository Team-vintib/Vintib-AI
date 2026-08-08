package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.request.AiQualityFindingRequest;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisStatus;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductDefect;
import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.ProductQualityFinding;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.port.dto.LinkedLiveSummary;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductDefectRepository;
import com.ssafy.backend.product.repository.ProductQualityFindingRepository;
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
    private static final ProductListFilterParams NO_FILTER =
            new ProductListFilterParams(null, null, null, null, null, null, null);

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
    private ProductQualityFindingRepository productQualityFindingRepository;

    @Mock
    private SocialQueryPort socialQueryPort;

    @Mock
    private LiveQueryPort liveQueryPort;

    @Mock
    private AiClient aiClient;

    @Mock
    private Member seller;

    private ProductService productService;

    @BeforeEach
    void setUp() {
        productService = new ProductService(
                productRepository, memberRepository, productImageService, categoryRepository,
                productDefectRepository, productQualityFindingRepository,
                socialQueryPort, liveQueryPort, aiClient);
    }

    @Test
    void 상품_기본_정보를_저장하면_saleType_없이_DRAFT_상태로_생성된다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, null, false, null);

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
                "리바이스",
                "A급",
                null,
                "M",
                "블랙",
                "데님",
                Map.of("총장", 70),
                List.of("소매 끝 실밥 풀림", "안감 얼룩"),
                null,
                false,
                null);

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
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, null, false, null);

        productService.createProduct(SELLER_ID, request);

        verify(productDefectRepository, never()).saveAll(any());
    }

    @Test
    void 존재하지_않는_판매자면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.empty());

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", null, CATEGORY_ID, null, null, null, null, null, null, null, null, null, false, null);

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
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, null, false, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.CATEGORY_NOT_FOUND);
        verify(productRepository, never()).save(any());
    }

    @Test
    void AI_착용컷을_활성화하면서_모델_성별을_지정하지_않으면_예외를_던진다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, null, true, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
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
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null, null,
                true, com.ssafy.backend.product.entity.AiModelGender.FEMALE);

        ArgumentCaptor<Product> captor = ArgumentCaptor.forClass(Product.class);
        productService.createProduct(SELLER_ID, request);

        verify(productRepository).save(captor.capture());
        assertThat(captor.getValue().isAiModelEnabled()).isTrue();
        assertThat(captor.getValue().getAiModelGender())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelGender.FEMALE);
    }

    @Test
    void 등록_시_확정한_AI_품질_검수_finding을_저장한다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(seller.getId()).thenReturn(SELLER_ID);
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", 78.0, "M", null, null, null, null,
                List.of(new AiQualityFindingRequest(
                        ProductImageRole.FRONT, "소매 끝단 마모 의심",
                        new AiQualityFindingRequest.Box(58, 18, 24, 18))),
                false, null);

        productService.createProduct(SELLER_ID, request);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<ProductQualityFinding>> captor = ArgumentCaptor.forClass(List.class);
        verify(productQualityFindingRepository).saveAll(captor.capture());
        List<ProductQualityFinding> saved = captor.getValue();
        assertThat(saved).hasSize(1);
        assertThat(saved.get(0).getPhotoRole()).isEqualTo(ProductImageRole.FRONT);
        assertThat(saved.get(0).getDescription()).isEqualTo("소매 끝단 마모 의심");
        assertThat(saved.get(0).getBox()).containsEntry("x", 58).containsEntry("width", 24);
    }

    @Test
    void ADDITIONAL_사진에는_AI_품질_검수_finding을_등록할_수_없다() {
        when(memberRepository.findById(SELLER_ID)).thenReturn(Optional.of(seller));
        when(categoryRepository.existsById(CATEGORY_ID)).thenReturn(true);
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProductCreateRequest request = new ProductCreateRequest(
                "빈티지 자켓", "설명", CATEGORY_ID, "리바이스", "A급", null, "M", null, null, null, null,
                List.of(new AiQualityFindingRequest(ProductImageRole.ADDITIONAL, "얼룩", null)),
                false, null);

        assertThatThrownBy(() -> productService.createProduct(SELLER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.AI_QUALITY_FINDING_INVALID_PHOTO_ROLE);
    }

    @Test
    void PENDING_상태의_착용컷_조회시_AI가_완료를_돌려주면_COMPLETED로_갱신된다() {
        Product product = Product.builder()
                .seller(seller)
                .title("빈티지 자켓")
                .aiModelEnabled(true)
                .aiModelGender(com.ssafy.backend.product.entity.AiModelGender.MALE)
                .build();
        product.startAiModelCutJob("job-123");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(aiClient.getJob("job-123")).thenReturn(new com.ssafy.backend.global.client.dto.AiJobResponse(
                "success", Map.of("image_url", "https://ai.example/result.png"), null));

        com.ssafy.backend.product.dto.response.ProductAiModelCutResponse response =
                productService.getAiModelCutStatus(1L);

        assertThat(response.status())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelCutStatus.COMPLETED);
        assertThat(response.imageUrl()).isEqualTo("https://ai.example/result.png");
    }

    @Test
    void NONE_상태의_착용컷은_AI를_조회하지_않고_그대로_반환한다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        com.ssafy.backend.product.dto.response.ProductAiModelCutResponse response =
                productService.getAiModelCutStatus(1L);

        assertThat(response.status())
                .isEqualTo(com.ssafy.backend.product.entity.AiModelCutStatus.NONE);
        verify(aiClient, never()).getJob(any());
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
    void 상품_목록_조회시_공개_상태_상품이_매핑된다() {
        Product onSale = Product.builder().seller(seller).title("상시 판매 상품").build();
        onSale.registerDirectSale(10000L);
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(onSale), pageable, 1));

        PageResponse<ProductResponse> response = productService.getProductList(NO_FILTER, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).saleStatus()).isEqualTo(SaleStatus.ON_SALE);
    }

    @Test
    void 상품_목록_조회시_페이지네이션_정보를_반환한다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        Pageable pageable = PageRequest.of(0, 2);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(product, product), pageable, 5));

        PageResponse<ProductResponse> response = productService.getProductList(NO_FILTER, pageable);

        assertThat(response.page()).isEqualTo(0);
        assertThat(response.size()).isEqualTo(2);
        assertThat(response.totalElements()).isEqualTo(5);
        assertThat(response.totalPages()).isEqualTo(3);
        assertThat(response.hasNext()).isTrue();
    }

    @Test
    void 상품_목록이_비어있으면_빈_배열을_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), pageable, 0));

        PageResponse<ProductResponse> response = productService.getProductList(NO_FILTER, pageable);

        assertThat(response.content()).isEmpty();
        assertThat(response.totalElements()).isZero();
    }

    @Test
    void 마이페이지_판매_상품_목록은_DRAFT_상품도_포함해_반환한다() {
        Product draft = Product.builder().seller(seller).title("등록 중 상품").build();
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findBySeller_IdOrderByCreatedAtDesc(SELLER_ID, pageable))
                .thenReturn(new PageImpl<>(List.of(draft), pageable, 1));

        PageResponse<ProductResponse> response = productService.getMyProducts(SELLER_ID, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).saleStatus()).isEqualTo(SaleStatus.DRAFT);
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
    void 등록된_finding이_없으면_AI_품질_검수_상태는_NOT_REQUESTED다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse response = productService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.NOT_REQUESTED);
        assertThat(response.aiQualityAnalysis().images()).isEmpty();
    }

    @Test
    void finding이_있으면_사진role별로_묶여_원본_이미지_URL과_함께_내려간다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductQualityFinding frontFinding = ProductQualityFinding.builder()
                .product(product)
                .photoRole(ProductImageRole.FRONT)
                .description("소매 끝단 마모 의심")
                .box(Map.of("x", 58, "y", 18, "width", 24, "height", 18))
                .sortOrder((short) 0)
                .build();
        when(productQualityFindingRepository.findAllByProductIdOrderBySortOrderAsc(1L))
                .thenReturn(List.of(frontFinding));
        when(productImageService.getImages(1L)).thenReturn(List.of(
                new ProductImageResponse(1L, "https://s3.example/front.jpg", (short) 0, true, ProductImageRole.FRONT),
                new ProductImageResponse(2L, "https://s3.example/etc.jpg", (short) 1, false, ProductImageRole.ADDITIONAL)));

        ProductDetailResponse response = productService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.COMPLETED);
        assertThat(response.aiQualityAnalysis().images()).hasSize(1);
        var frontImage = response.aiQualityAnalysis().images().get(0);
        assertThat(frontImage.label()).isEqualTo("앞면");
        assertThat(frontImage.originalImageUrl()).isEqualTo("https://s3.example/front.jpg");
        assertThat(frontImage.analyzedImageUrl()).isEqualTo("https://s3.example/front.jpg");
        assertThat(frontImage.summary()).isNull();
        assertThat(frontImage.findings()).hasSize(1);
        assertThat(frontImage.findings().get(0).description()).isEqualTo("소매 끝단 마모 의심");
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

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);
        ProductResponse response = productService.updateProduct(SELLER_ID, 1L, request);

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
                null, null, null, null, null, null, "블랙", "데님", Map.of("총장", 70), null, null, null);
        productService.updateProduct(SELLER_ID, 1L, request);

        assertThat(product.getColor()).isEqualTo("블랙");
        assertThat(product.getMaterial()).isEqualTo("데님");
        assertThat(product.getMeasurements()).isEqualTo(Map.of("총장", 70));
    }

    @Test
    void 하자_목록을_보내면_기존_것을_지우고_새로_저장한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, List.of("얼룩"), null, null);
        productService.updateProduct(SELLER_ID, 1L, request);

        verify(productDefectRepository).deleteAllByProductId(1L);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<ProductDefect>> captor = ArgumentCaptor.forClass(List.class);
        verify(productDefectRepository).saveAll(captor.capture());
        assertThat(captor.getValue()).hasSize(1);
        assertThat(captor.getValue().get(0).getContent()).isEqualTo("얼룩");
    }

    @Test
    void 하자를_빈_배열로_보내면_기존_하자를_전부_삭제하고_새로_저장하지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest(null, null, null, null, null, null, null, null, null, List.of(), null, null);
        productService.updateProduct(SELLER_ID, 1L, request);

        verify(productDefectRepository).deleteAllByProductId(1L);
        verify(productDefectRepository, never()).saveAll(any());
    }

    @Test
    void 하자가_null이면_기존_하자를_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);
        productService.updateProduct(SELLER_ID, 1L, request);

        verify(productDefectRepository, never()).deleteAllByProductId(any());
        verify(productDefectRepository, never()).saveAll(any());
    }

    @Test
    void AI_품질_검수_finding을_보내면_기존_것을_지우고_새로_저장한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request = new ProductUpdateRequest(
                null, null, null, null, null, null, null, null, null, null,
                List.of(new AiQualityFindingRequest(
                        ProductImageRole.BACK, "밑단 오염",
                        new AiQualityFindingRequest.Box(10, 20, 30, 40))),
                null);
        productService.updateProduct(SELLER_ID, 1L, request);

        verify(productQualityFindingRepository).deleteAllByProductId(1L);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<ProductQualityFinding>> captor = ArgumentCaptor.forClass(List.class);
        verify(productQualityFindingRepository).saveAll(captor.capture());
        assertThat(captor.getValue()).hasSize(1);
        assertThat(captor.getValue().get(0).getPhotoRole()).isEqualTo(ProductImageRole.BACK);
        assertThat(captor.getValue().get(0).getDescription()).isEqualTo("밑단 오염");
    }

    @Test
    void AI_품질_검수_finding이_null이면_기존_finding을_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);
        productService.updateProduct(SELLER_ID, 1L, request);

        verify(productQualityFindingRepository, never()).deleteAllByProductId(any());
        verify(productQualityFindingRepository, never()).saveAll(any());
    }

    @Test
    void 본인이_아니면_수정시_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productService.updateProduct(2L, 1L, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 수정_불가_상태면_예외를_던진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.SOLD);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);

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

        ProductUpdateRequest request =
                new ProductUpdateRequest(null, null, CATEGORY_ID, null, null, null, null, null, null, null, null, null);

        assertThatThrownBy(() -> productService.updateProduct(SELLER_ID, 1L, request))
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
                null, null, null, null, null, null, null, null, null, null, null, 45_000L);
        ProductResponse response = productService.updateProduct(SELLER_ID, 1L, request);

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
                null, null, null, null, null, null, null, null, null, null, null, 45_000L);

        assertThatThrownBy(() -> productService.updateProduct(SELLER_ID, 1L, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_PRODUCT_STATE);
    }

    @Test
    void 가격이_없으면_기존_가격을_건드리지_않는다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.registerDirectSale(50_000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductUpdateRequest request =
                new ProductUpdateRequest("수정된 제목", null, null, null, null, null, null, null, null, null, null, null);
        ProductResponse response = productService.updateProduct(SELLER_ID, 1L, request);

        assertThat(response.price()).isEqualTo(50_000L);
    }

    // -----------------------------------------------------------------------
    // 상품 목록 필터·정렬 (PROD-008)
    // -----------------------------------------------------------------------

    @Test
    void 필터_없이_조회하면_findWithFilter에_모든_플래그가_false로_전달된다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        when(productRepository.findWithFilter(
                eq(false), any(), eq(false), any(), eq(false), any(),
                eq(false), any(), eq(false), any(), eq(false), any(), any(Pageable.class)))
                .thenReturn(emptyPage);

        ProductListFilterParams filter =
                new ProductListFilterParams(null, null, null, null, null, null, null);

        // when
        PageResponse<ProductResponse> response =
                productService.getProductList(filter, PageRequest.of(0, 20));

        // then
        assertThat(response.content()).isEmpty();
    }

    @Test
    void 카테고리_필터를_주면_hasCategoryFilter_true로_전달된다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        ArgumentCaptor<Boolean> flagCaptor = ArgumentCaptor.forClass(Boolean.class);
        when(productRepository.findWithFilter(
                flagCaptor.capture(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(emptyPage);

        ProductListFilterParams filter =
                new ProductListFilterParams(List.of(1L, 2L), null, null, null, null, null, null);

        // when
        productService.getProductList(filter, PageRequest.of(0, 20));

        // then: 첫 번째 캡처 = hasCategoryFilter
        assertThat(flagCaptor.getValue()).isTrue();
    }

    @Test
    void 판매자_필터를_주면_hasSellerFilter가_true로_전달되고_sellerId가_그대로_넘어간다() {
        // given: 공개 프로필(011 §3.5)에서 특정 판매자 상품만 조회할 때 쓴다.
        Page<Product> emptyPage = new PageImpl<>(List.of());
        ArgumentCaptor<Boolean> flagCaptor = ArgumentCaptor.forClass(Boolean.class);
        ArgumentCaptor<Long> sellerIdCaptor = ArgumentCaptor.forClass(Long.class);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(),
                flagCaptor.capture(), sellerIdCaptor.capture(), any(Pageable.class)))
                .thenReturn(emptyPage);

        ProductListFilterParams filter =
                new ProductListFilterParams(null, null, null, null, null, null, SELLER_ID);

        // when
        productService.getProductList(filter, PageRequest.of(0, 20));

        // then
        assertThat(flagCaptor.getValue()).isTrue();
        assertThat(sellerIdCaptor.getValue()).isEqualTo(SELLER_ID);
    }

    @Test
    void 판매자_필터가_없으면_hasSellerFilter가_false로_전달된다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), eq(false), any(), any(Pageable.class)))
                .thenReturn(emptyPage);

        // when
        productService.getProductList(NO_FILTER, PageRequest.of(0, 20));

        // then: eq(false)로 스텁된 호출이 실제로 매치됐다면(즉 예외 없이) 통과
        verify(productRepository).findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), eq(false), any(), any(Pageable.class));
    }

    @Test
    void 가격_범위_필터를_주면_hasMinPrice와_hasMaxPrice가_true로_전달된다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Boolean> captors = ArgumentCaptor.forClass(Boolean.class);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                captors.capture(), any(), captors.capture(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(emptyPage);

        ProductListFilterParams filter =
                new ProductListFilterParams(null, null, null, 10_000L, 50_000L, null, null);

        // when
        productService.getProductList(filter, PageRequest.of(0, 20));

        // then: hasMinPrice, hasMaxPrice 모두 true
        assertThat(captors.getAllValues()).containsOnly(true);
    }

    @Test
    void PRICE_ASC_정렬이면_pageable에_price_오름차순이_담긴다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), pageableCaptor.capture()))
                .thenReturn(emptyPage);

        ProductListFilterParams filter =
                new ProductListFilterParams(null, null, null, null, null, ProductSortType.PRICE_ASC, null);

        // when
        productService.getProductList(filter, PageRequest.of(0, 20));

        // then
        Pageable captured = pageableCaptor.getValue();
        assertThat(captured.getSort().getOrderFor("price")).isNotNull();
        assertThat(captured.getSort().getOrderFor("price").getDirection())
                .isEqualTo(org.springframework.data.domain.Sort.Direction.ASC);
    }

    @Test
    void sort_미입력이면_기본값_LATEST로_createdAt_DESC_정렬이_적용된다() {
        // given
        Page<Product> emptyPage = new PageImpl<>(List.of());
        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), pageableCaptor.capture()))
                .thenReturn(emptyPage);

        // sort=null → resolvedSort()=LATEST
        ProductListFilterParams filter =
                new ProductListFilterParams(null, null, null, null, null, null, null);

        // when
        productService.getProductList(filter, PageRequest.of(0, 20));

        // then
        Pageable captured = pageableCaptor.getValue();
        assertThat(captured.getSort().getOrderFor("createdAt")).isNotNull();
        assertThat(captured.getSort().getOrderFor("createdAt").getDirection())
                .isEqualTo(org.springframework.data.domain.Sort.Direction.DESC);
    }

    @Test
    void 상품_상세조회시_연결라이브_찜_판매자통계를_함께_반환한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder()
                .seller(seller)
                .categoryId(CATEGORY_ID)
                .brand("리바이스")
                .title("빈티지 자켓")
                .build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(productRepository.countBySeller_IdAndSaleStatusNot(SELLER_ID, SaleStatus.DRAFT)).thenReturn(45L);
        when(socialQueryPort.countFollowers(SELLER_ID)).thenReturn(120L);
        when(socialQueryPort.isWishedBy(1L, 2L)).thenReturn(true);

        Category category = org.mockito.Mockito.mock(Category.class);
        when(category.getName()).thenReturn("자켓");
        when(categoryRepository.findById(CATEGORY_ID)).thenReturn(Optional.of(category));

        LinkedLiveSummary liveSummary = LinkedLiveSummary.builder()
                .liveId(10L).title("빈티지 특가").status("SCHEDULED").build();
        when(liveQueryPort.findLinkedLive(1L)).thenReturn(Optional.of(liveSummary));

        ProductDetailResponse response = productService.getProductDetail(2L, 1L);

        assertThat(response.categoryName()).isEqualTo("자켓");
        assertThat(response.brand()).isEqualTo("리바이스");
        assertThat(response.isWished()).isTrue();
        assertThat(response.sellerFollowerCount()).isEqualTo(120L);
        assertThat(response.sellerProductCount()).isEqualTo(45L);
        assertThat(response.linkedLive()).isNotNull();
        assertThat(response.linkedLive().liveId()).isEqualTo(10L);
        assertThat(response.linkedLive().title()).isEqualTo("빈티지 특가");
        assertThat(response.linkedLive().status()).isEqualTo("SCHEDULED");
    }

    @Test
    void 상품_상세조회시_유사_상품_목록을_그대로_담아_반환한다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder()
                .seller(seller)
                .categoryId(CATEGORY_ID)
                .brand("리바이스")
                .title("빈티지 자켓")
                .build();
        product.registerDirectSale(50000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        Member otherSeller = org.mockito.Mockito.mock(Member.class);
        Product sameBrand = Product.builder()
                .seller(otherSeller).categoryId(CATEGORY_ID).brand("리바이스").title("같은 브랜드 상품").build();
        ReflectionTestUtils.setField(sameBrand, "id", 2L);
        sameBrand.registerDirectSale(70000L);
        when(productRepository.findSimilarProducts(
                eq(CATEGORY_ID), eq(1L), eq("리바이스"), any(Pageable.class)))
                .thenReturn(List.of(sameBrand));

        ProductDetailResponse response = productService.getProductDetail(2L, 1L);

        assertThat(response.similarProducts()).hasSize(1);
        assertThat(response.similarProducts().get(0).id()).isEqualTo(2L);
        assertThat(response.similarProducts().get(0).title()).isEqualTo("같은 브랜드 상품");
        assertThat(response.similarProducts().get(0).price()).isEqualTo(70000L);
    }
}
