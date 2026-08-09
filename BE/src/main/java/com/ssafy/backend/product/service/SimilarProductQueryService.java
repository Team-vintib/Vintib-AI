package com.ssafy.backend.product.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.dto.response.SimilarProductsResponse;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SimilarProductCandidate;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.product.repository.SimilarProductCandidateRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 유사 상품 추천 서빙(CH034). {@link SimilarProductCacheService}가 배치로 미리 채운 캐시만
 * 읽는다 — 이 클래스는 AI를 절대 호출하지 않는다(AI 서버 상태가 상품 상세 페이지에 영향을
 * 주면 안 된다는 요구사항, {@code docs/requests/BE/042}).
 *
 * <p>캐시 후보를 실시간 판매상태로 다시 거른 뒤(배치 계산 이후 품절된 상품 배제), 남은
 * 개수가 {@link #FULL_FALLBACK_MAX_COUNT} 이하면 AI 신호를 아예 버리고 기존
 * {@link ProductRepository#findSimilarProducts} SQL로 전체 대체한다 — 그만큼 적으면 AI
 * 판단을 신뢰하기 어렵다고 본다. 그보다 많으면 그대로 쓰되, 캐러셀 한 슬라이드
 * ({@link #TARGET_DISPLAY_COUNT}개)를 못 채우면 SQL로 부족분만 보충한다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class SimilarProductQueryService {

    /** 캐시 필터링 후 이 개수 이하로 남으면 AI 신호를 버리고 SQL로 전체 대체한다("2개면 폴백"). */
    private static final int FULL_FALLBACK_MAX_COUNT = 2;

    /** 캐러셀 한 슬라이드 분량 — 이 개수까지는 SQL로 보충해서라도 채운다. */
    private static final int TARGET_DISPLAY_COUNT = 5;

    /** 응답 상한. 기존 {@code ProductService.SIMILAR_PRODUCT_LIMIT}과 동일한 기준. */
    private static final int RESPONSE_LIMIT = 20;

    // AI는 판매상태를 모른다 — 캐시된 후보든 SQL 폴백이든 항상 이 상태로 다시 걸러야 한다.
    private static final List<SaleStatus> ELIGIBLE_STATUSES =
            List.of(SaleStatus.ON_SALE, SaleStatus.AUCTION_SCHEDULED, SaleStatus.AUCTION_IN_PROGRESS);

    private final ProductRepository productRepository;
    private final SimilarProductCandidateRepository candidateRepository;
    private final ProductImageService productImageService;

    public SimilarProductsResponse getSimilarProducts(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        List<Product> chosen = resolveCandidates(product);

        List<Long> imageTargetIds = chosen.stream().map(Product::getId).toList();
        Map<Long, String> primaryImageUrls = productImageService.getPrimaryImageUrls(imageTargetIds);

        List<ProductResponse> items = chosen.stream()
                .map(p -> ProductResponse.from(p, primaryImageUrls.get(p.getId())))
                .toList();

        return new SimilarProductsResponse(productId, items);
    }

    private List<Product> resolveCandidates(Product product) {
        List<Product> aiCandidates = liveAiCandidates(product);

        if (aiCandidates.size() <= FULL_FALLBACK_MAX_COUNT) {
            return sqlFallback(product, Set.of(), RESPONSE_LIMIT);
        }

        List<Product> result = new ArrayList<>(aiCandidates);
        if (result.size() < TARGET_DISPLAY_COUNT) {
            Set<Long> excludeIds = result.stream().map(Product::getId).collect(Collectors.toSet());
            excludeIds.add(product.getId());
            int needed = TARGET_DISPLAY_COUNT - result.size();
            result.addAll(sqlFallback(product, excludeIds, needed));
        }
        return result;
    }

    /** 캐시된 후보를 순위 그대로 읽고, 지금 시점 실제 판매상태로 다시 거른다. */
    private List<Product> liveAiCandidates(Product product) {
        List<SimilarProductCandidate> cached =
                candidateRepository.findByProductIdOrderByRankAsc(product.getId());
        if (cached.isEmpty()) {
            return List.of();
        }

        List<Long> candidateIds = cached.stream().map(SimilarProductCandidate::getSimilarProductId).toList();
        Map<Long, Product> productsById = productRepository.findAllById(candidateIds).stream()
                .collect(Collectors.toMap(Product::getId, Function.identity()));

        List<Product> live = new ArrayList<>();
        for (SimilarProductCandidate candidate : cached) {
            Product candidateProduct = productsById.get(candidate.getSimilarProductId());
            if (candidateProduct != null && ELIGIBLE_STATUSES.contains(candidateProduct.getSaleStatus())) {
                live.add(candidateProduct);
            }
            if (live.size() >= RESPONSE_LIMIT) {
                break;
            }
        }
        return live;
    }

    /** 기존 카테고리+브랜드 SQL(PROD-006/011)로 {@code limit}개까지 채운다. {@code excludeIds}는 이미 포함된 상품. */
    private List<Product> sqlFallback(Product product, Set<Long> excludeIds, int limit) {
        if (limit <= 0) {
            return List.of();
        }
        return productRepository.findSimilarProducts(
                        product.getCategoryId(), product.getId(), product.getBrand(),
                        PageRequest.of(0, RESPONSE_LIMIT))
                .stream()
                .filter(p -> ELIGIBLE_STATUSES.contains(p.getSaleStatus()))
                .filter(p -> !excludeIds.contains(p.getId()))
                .limit(limit)
                .toList();
    }
}
