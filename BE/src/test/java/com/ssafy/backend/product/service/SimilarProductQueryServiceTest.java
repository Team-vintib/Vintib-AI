package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.dto.response.SimilarProductsResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SimilarProductCandidate;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.product.repository.SimilarProductCandidateRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * {@link SimilarProductQueryService} 단위 테스트(CH034). AI 캐시가 부족할 때 SQL로 보충하는
 * 임계값(2개 이하는 전체 폴백, 그 외엔 슬라이드 목표(5개)까지만 보충)을 중점적으로 본다.
 */
@ExtendWith(MockitoExtension.class)
class SimilarProductQueryServiceTest {

    private static final Long CATEGORY_ID = 10L;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private SimilarProductCandidateRepository candidateRepository;

    @Mock
    private ProductImageService productImageService;

    private SimilarProductQueryService service;

    private void setUpService() {
        service = new SimilarProductQueryService(productRepository, candidateRepository, productImageService);
    }

    private Product product(Long id, SaleStatus saleStatus) {
        Member seller = mock(Member.class);
        Product product = Product.builder()
                .seller(seller)
                .categoryId(CATEGORY_ID)
                .brand("리바이스")
                .title("상품 " + id)
                .build();
        ReflectionTestUtils.setField(product, "id", id);
        ReflectionTestUtils.setField(product, "saleStatus", saleStatus);
        return product;
    }

    private SimilarProductCandidate candidate(Long similarProductId, int rank) {
        return SimilarProductCandidate.builder()
                .productId(1L)
                .similarProductId(similarProductId)
                .score(1.0 - rank * 0.01)
                .rank(rank)
                .computedAt(LocalDateTime.now())
                .build();
    }

    @Test
    void 상품이_없으면_예외를_던진다() {
        setUpService();
        when(productRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.getSimilarProducts(1L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 캐시가_비어있으면_SQL_폴백만_쓴다() {
        setUpService();
        Product source = product(1L, SaleStatus.ON_SALE);
        when(productRepository.findById(1L)).thenReturn(Optional.of(source));
        when(candidateRepository.findByProductIdOrderByRankAsc(1L)).thenReturn(List.of());

        Product fallback = product(2L, SaleStatus.ON_SALE);
        when(productRepository.findSimilarProducts(eq(CATEGORY_ID), eq(1L), eq("리바이스"), any(Pageable.class)))
                .thenReturn(List.of(fallback));

        SimilarProductsResponse response = service.getSimilarProducts(1L);

        assertThat(response.items()).extracting(i -> i.id()).containsExactly(2L);
    }

    @Test
    void 판매상태_필터링_후_2개_이하면_AI_신호를_버리고_SQL로_전체_대체한다() {
        setUpService();
        Product source = product(1L, SaleStatus.ON_SALE);
        when(productRepository.findById(1L)).thenReturn(Optional.of(source));

        // 캐시엔 3개가 있지만 그중 1개는 이미 품절(SOLD)돼 살아남는 건 2개뿐 -> 임계값(2) 이하.
        when(candidateRepository.findByProductIdOrderByRankAsc(1L))
                .thenReturn(List.of(candidate(2L, 0), candidate(3L, 1), candidate(4L, 2)));
        Product live1 = product(2L, SaleStatus.ON_SALE);
        Product live2 = product(3L, SaleStatus.ON_SALE);
        Product sold = product(4L, SaleStatus.SOLD);
        when(productRepository.findAllById(List.of(2L, 3L, 4L))).thenReturn(List.of(live1, live2, sold));

        Product fallback = product(9L, SaleStatus.ON_SALE);
        when(productRepository.findSimilarProducts(eq(CATEGORY_ID), eq(1L), eq("리바이스"), any(Pageable.class)))
                .thenReturn(List.of(fallback));

        SimilarProductsResponse response = service.getSimilarProducts(1L);

        // AI가 준 2/3도 버리고 SQL 결과(9L)만 쓴다.
        assertThat(response.items()).extracting(i -> i.id()).containsExactly(9L);
    }

    @Test
    void 판매상태_필터링_후_3개_이상이면_AI_순서_그대로_쓰고_슬라이드_목표까지_SQL로_보충한다() {
        setUpService();
        Product source = product(1L, SaleStatus.ON_SALE);
        when(productRepository.findById(1L)).thenReturn(Optional.of(source));

        when(candidateRepository.findByProductIdOrderByRankAsc(1L))
                .thenReturn(List.of(candidate(2L, 0), candidate(3L, 1), candidate(4L, 2)));
        Product ai1 = product(2L, SaleStatus.ON_SALE);
        Product ai2 = product(3L, SaleStatus.AUCTION_IN_PROGRESS);
        Product ai3 = product(4L, SaleStatus.ON_SALE);
        when(productRepository.findAllById(List.of(2L, 3L, 4L))).thenReturn(List.of(ai1, ai2, ai3));

        // 목표(5개)까지 2개 부족 -> SQL에서 2개만 가져와야 한다(이미 포함된 2/3/4는 제외).
        Product fallback1 = product(5L, SaleStatus.ON_SALE);
        Product fallback2 = product(6L, SaleStatus.ON_SALE);
        Product alreadyIncluded = product(2L, SaleStatus.ON_SALE);
        when(productRepository.findSimilarProducts(eq(CATEGORY_ID), eq(1L), eq("리바이스"), any(Pageable.class)))
                .thenReturn(List.of(alreadyIncluded, fallback1, fallback2));

        SimilarProductsResponse response = service.getSimilarProducts(1L);

        assertThat(response.items()).extracting(i -> i.id()).containsExactly(2L, 3L, 4L, 5L, 6L);
    }

    @Test
    void 판매상태_필터링_후_슬라이드_목표를_이미_채웠으면_SQL_보충을_호출하지_않는다() {
        setUpService();
        Product source = product(1L, SaleStatus.ON_SALE);
        when(productRepository.findById(1L)).thenReturn(Optional.of(source));

        List<SimilarProductCandidate> cached = List.of(
                candidate(2L, 0), candidate(3L, 1), candidate(4L, 2), candidate(5L, 3), candidate(6L, 4));
        when(candidateRepository.findByProductIdOrderByRankAsc(1L)).thenReturn(cached);
        List<Product> liveProducts = List.of(
                product(2L, SaleStatus.ON_SALE),
                product(3L, SaleStatus.ON_SALE),
                product(4L, SaleStatus.ON_SALE),
                product(5L, SaleStatus.ON_SALE),
                product(6L, SaleStatus.ON_SALE));
        when(productRepository.findAllById(anyCollection())).thenReturn(liveProducts);

        SimilarProductsResponse response = service.getSimilarProducts(1L);

        assertThat(response.items()).extracting(i -> i.id()).containsExactly(2L, 3L, 4L, 5L, 6L);
        org.mockito.Mockito.verify(productRepository, org.mockito.Mockito.never())
                .findSimilarProducts(any(), any(), any(), any());
    }
}
