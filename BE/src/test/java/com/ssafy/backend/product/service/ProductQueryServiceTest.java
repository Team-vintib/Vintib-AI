package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.response.AiQualityAnalysisStatus;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductMarketPriceResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.ProductImageRole;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.OrderQueryPort;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.port.dto.CompletedOrderSummary;
import com.ssafy.backend.product.port.dto.LinkedLiveSummary;
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
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class ProductQueryServiceTest {

    private static final Long SELLER_ID = 1L;
    private static final Long CATEGORY_ID = 10L;
    private static final ProductListFilterParams NO_FILTER =
            new ProductListFilterParams(null, null, null, null, null, null, null);

    @Mock
    private ProductRepository productRepository;

    @Mock
    private ProductImageService productImageService;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private SocialQueryPort socialQueryPort;

    @Mock
    private LiveQueryPort liveQueryPort;

    @Mock
    private OrderQueryPort orderQueryPort;

    @Mock
    private Member seller;

    private ProductQueryService productQueryService;

    @BeforeEach
    void setUp() {
        productQueryService = new ProductQueryService(
                productRepository, productImageService, categoryRepository,
                socialQueryPort, liveQueryPort, orderQueryPort);
    }

    @Test
    void 상품_목록_조회시_공개_상태_상품이_매핑된다() {
        Product onSale = Product.builder().seller(seller).title("정찰제 상품").build();
        onSale.registerDirectSale(10000L);
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findWithFilter(
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(),
                anyBoolean(), any(), anyBoolean(), any(), anyBoolean(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(onSale), pageable, 1));

        PageResponse<ProductResponse> response = productQueryService.getProductList(NO_FILTER, pageable);

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

        PageResponse<ProductResponse> response = productQueryService.getProductList(NO_FILTER, pageable);

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

        PageResponse<ProductResponse> response = productQueryService.getProductList(NO_FILTER, pageable);

        assertThat(response.content()).isEmpty();
        assertThat(response.totalElements()).isZero();
    }

    @Test
    void 마이페이지_판매_상품_목록은_DRAFT_상품도_포함해_반환한다() {
        Product draft = Product.builder().seller(seller).title("등록 중 상품").build();
        Pageable pageable = PageRequest.of(0, 20);
        when(productRepository.findBySeller_IdOrderByCreatedAtDesc(SELLER_ID, pageable))
                .thenReturn(new PageImpl<>(List.of(draft), pageable, 1));

        PageResponse<ProductResponse> response = productQueryService.getMyProducts(SELLER_ID, pageable);

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

        ProductDetailResponse loggedOutResponse = productQueryService.getProductDetail(null, 1L);
        ProductDetailResponse otherViewerResponse = productQueryService.getProductDetail(2L, 1L);

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

        ProductDetailResponse ownerResponse = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(ownerResponse.saleStatus()).isEqualTo(SaleStatus.DRAFT);
        assertThatThrownBy(() -> productQueryService.getProductDetail(2L, 1L))
                .isInstanceOf(CustomException.class);
        assertThatThrownBy(() -> productQueryService.getProductDetail(null, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 존재하지_않는_상품을_조회하면_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productQueryService.getProductDetail(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 삭제된_상품은_상세조회시_404가_된다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.softDelete();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> productQueryService.getProductDetail(SELLER_ID, 1L))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 검수_job_자체가_없으면_AI_품질_검수_상태는_NOT_REQUESTED다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.NOT_REQUESTED);
        assertThat(response.aiQualityAnalysis().images()).isEmpty();
    }

    @Test
    void 검수_job이_진행중이면_AI_품질_검수_상태는_ANALYZING이다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.startQualityInspectionJob("job-1");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.ANALYZING);
    }

    @Test
    void 검수_job이_실패하면_AI_품질_검수_상태는_FAILED다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.failQualityInspectionJob();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.FAILED);
    }

    @Test
    void 검수가_끝났는데_인정된_finding이_0건이면_NO_FINDINGS다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        product.completeQualityInspectionJob(Map.of("findings", List.of()));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.NO_FINDINGS);
        assertThat(response.aiQualityAnalysis().images()).isEmpty();
    }

    @Test
    void finding이_있으면_원본_그대로_사진role별로_묶여_내려간다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        Map<String, Object> qualityResult = Map.of(
                "findings", List.of(Map.of(
                        "key", "hole_tear_0_9_1",
                        "label", "구멍·찢어짐",
                        "section", "HEM_RIGHT",
                        "description", "구멍이 생긴 부분이 확인됩니다.",
                        "no", 1,
                        "image_index", 0,
                        "bbox", List.of(0.58, 0.18, 0.82, 0.36))),
                "image_summaries", List.of(Map.of("image_index", 0, "summary", "1. 오른쪽 밑단 구멍·찢어짐")));
        product.completeQualityInspectionJob(qualityResult);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(productImageService.getImages(1L)).thenReturn(List.of(
                new ProductImageResponse(1L, "https://s3.example/front.jpg", (short) 0, true, ProductImageRole.FRONT),
                new ProductImageResponse(2L, "https://s3.example/etc.jpg", (short) 1, false, ProductImageRole.ADDITIONAL)));

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        assertThat(response.aiQualityAnalysis().status()).isEqualTo(AiQualityAnalysisStatus.COMPLETED);
        assertThat(response.aiQualityAnalysis().images()).hasSize(1);
        var frontImage = response.aiQualityAnalysis().images().get(0);
        assertThat(frontImage.label()).isEqualTo("앞면");
        assertThat(frontImage.originalImageUrl()).isEqualTo("https://s3.example/front.jpg");
        assertThat(frontImage.analyzedImageUrl()).isEqualTo("https://s3.example/front.jpg");
        assertThat(frontImage.summary()).isEqualTo("1. 오른쪽 밑단 구멍·찢어짐");
        assertThat(frontImage.findings()).hasSize(1);
        var finding = frontImage.findings().get(0);
        assertThat(finding.key()).isEqualTo("hole_tear_0_9_1");
        assertThat(finding.type()).isEqualTo("구멍·찢어짐");
        assertThat(finding.location()).isEqualTo("HEM_RIGHT");
        assertThat(finding.description()).isEqualTo("구멍이 생긴 부분이 확인됩니다.");
        assertThat(finding.no()).isEqualTo(1);
        assertThat(finding.box().x()).isCloseTo(58.0, org.assertj.core.data.Offset.offset(0.001));
        assertThat(finding.box().y()).isCloseTo(18.0, org.assertj.core.data.Offset.offset(0.001));
        assertThat(finding.box().width()).isCloseTo(24.0, org.assertj.core.data.Offset.offset(0.001));
        assertThat(finding.box().height()).isCloseTo(18.0, org.assertj.core.data.Offset.offset(0.001));
        assertThat(finding.isExcluded()).isFalse();
    }

    @Test
    void 제외된_key의_finding도_내려가되_isExcluded가_true다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("판매자");
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        Map<String, Object> rawFinding = new java.util.HashMap<>();
        rawFinding.put("key", "hole_tear_0_2_1");
        rawFinding.put("label", "구멍·찢어짐");
        rawFinding.put("section", "COLLAR");
        rawFinding.put("description", null);
        rawFinding.put("no", 1);
        rawFinding.put("image_index", 0);
        rawFinding.put("bbox", List.of(0.30, 0.19, 0.36, 0.22));
        Map<String, Object> qualityResult = Map.of("findings", List.of(rawFinding));
        product.completeQualityInspectionJob(qualityResult);
        ReflectionTestUtils.setField(product, "excludedQualityFindingKeys", List.of("hole_tear_0_2_1"));
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(productImageService.getImages(1L)).thenReturn(List.of());

        ProductDetailResponse response = productQueryService.getProductDetail(SELLER_ID, 1L);

        var finding = response.aiQualityAnalysis().images().get(0).findings().get(0);
        assertThat(finding.isExcluded()).isTrue();
        assertThat(finding.description()).isNull();
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
                productQueryService.getProductList(filter, PageRequest.of(0, 20));

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
        productQueryService.getProductList(filter, PageRequest.of(0, 20));

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
        productQueryService.getProductList(filter, PageRequest.of(0, 20));

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
        productQueryService.getProductList(NO_FILTER, PageRequest.of(0, 20));

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
        productQueryService.getProductList(filter, PageRequest.of(0, 20));

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
        productQueryService.getProductList(filter, PageRequest.of(0, 20));

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
        productQueryService.getProductList(filter, PageRequest.of(0, 20));

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

        ProductDetailResponse response = productQueryService.getProductDetail(2L, 1L);

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

        ProductDetailResponse response = productQueryService.getProductDetail(2L, 1L);

        assertThat(response.similarProducts()).hasSize(1);
        assertThat(response.similarProducts().get(0).id()).isEqualTo(2L);
        assertThat(response.similarProducts().get(0).title()).isEqualTo("같은 브랜드 상품");
        assertThat(response.similarProducts().get(0).price()).isEqualTo(70000L);
    }

    // --- 동일 상품 시세(CH001, 047) ------------------------------------------------

    @Test
    void matchKey가_없으면_빈_목록을_반환한다() {
        Product product = Product.builder().seller(seller).title("빈티지 자켓").build();
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        ProductMarketPriceResponse response = productQueryService.getMarketPrice(1L);

        assertThat(response.matchKey()).isNull();
        assertThat(response.listings()).isEmpty();
        assertThat(response.currentProduct()).isNull();
    }

    @Test
    void 상품이_없으면_예외를_던진다() {
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productQueryService.getMarketPrice(1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 같은_matchKey_상품들의_호가_완료거래가를_priceKind로_구분해_반환한다() {
        Product product = Product.builder().seller(seller).title("리바이스 501").build();
        ReflectionTestUtils.setField(product, "id", 1L);
        ReflectionTestUtils.setField(product, "matchKey", "1:501-리바이스:97");
        product.registerDirectSale(45000L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        Product asking = Product.builder().seller(seller).title("리바이스 501 (호가)").build();
        ReflectionTestUtils.setField(asking, "id", 2L);
        asking.registerDirectSale(48000L);

        Product soldDirect = Product.builder().seller(seller).title("리바이스 501 (직접판매완료)").build();
        ReflectionTestUtils.setField(soldDirect, "id", 3L);
        ReflectionTestUtils.setField(soldDirect, "saleStatus", SaleStatus.SOLD);

        Product soldAuction = Product.builder().seller(seller).title("리바이스 501 (경매낙찰)").build();
        ReflectionTestUtils.setField(soldAuction, "id", 4L);
        ReflectionTestUtils.setField(soldAuction, "saleStatus", SaleStatus.SOLD);

        when(productRepository.findByMatchKeyAndIdNot(eq("1:501-리바이스:97"), eq(1L), any(Pageable.class)))
                .thenReturn(List.of(asking, soldDirect, soldAuction));
        when(orderQueryPort.findCompletedOrders(any()))
                .thenReturn(List.of(
                        CompletedOrderSummary.builder().productId(3L).orderPrice(40000L).auctionWin(false).build(),
                        CompletedOrderSummary.builder().productId(4L).orderPrice(42000L).auctionWin(true).build()));

        ProductMarketPriceResponse response = productQueryService.getMarketPrice(1L);

        assertThat(response.matchKey()).isEqualTo("1:501-리바이스:97");
        assertThat(response.currentProduct().price()).isEqualTo(45000L);
        assertThat(response.currentProduct().priceKind()).isEqualTo("ASKING");
        assertThat(response.listings()).hasSize(3);
        assertThat(response.listings())
                .extracting(ProductMarketPriceResponse.Item::priceKind)
                .containsExactlyInAnyOrder("ASKING", "SOLD_DIRECT", "SOLD_AUCTION");
        assertThat(response.listings())
                .filteredOn(item -> item.priceKind().equals("SOLD_DIRECT"))
                .extracting(ProductMarketPriceResponse.Item::price)
                .containsExactly(40000L);
        assertThat(response.listings())
                .filteredOn(item -> item.priceKind().equals("SOLD_AUCTION"))
                .extracting(ProductMarketPriceResponse.Item::price)
                .containsExactly(42000L);
    }

    @Test
    void SOLD인데_완료거래_근거를_못_찾으면_목록에서_제외한다() {
        Product product = Product.builder().seller(seller).title("리바이스 501").build();
        ReflectionTestUtils.setField(product, "id", 1L);
        ReflectionTestUtils.setField(product, "matchKey", "1:501-리바이스:97");

        Product soldNoOrder = Product.builder().seller(seller).title("근거없음").build();
        ReflectionTestUtils.setField(soldNoOrder, "id", 5L);
        ReflectionTestUtils.setField(soldNoOrder, "saleStatus", SaleStatus.SOLD);

        when(productRepository.findById(1L)).thenReturn(Optional.of(product));
        when(productRepository.findByMatchKeyAndIdNot(eq("1:501-리바이스:97"), eq(1L), any(Pageable.class)))
                .thenReturn(List.of(soldNoOrder));
        when(orderQueryPort.findCompletedOrders(any())).thenReturn(List.of());

        ProductMarketPriceResponse response = productQueryService.getMarketPrice(1L);

        assertThat(response.listings()).isEmpty();
    }
}
