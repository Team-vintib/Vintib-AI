package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.SimilarProductAiResponse;
import com.ssafy.backend.product.entity.SimilarProductCandidate;
import com.ssafy.backend.product.repository.SimilarProductCandidateRepository;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * AI CLIP 유사 상품 후보를 배치로 미리 계산해 캐시에 채운다(CH034, {@code docs/requests/BE/042}).
 *
 * <p>서빙 경로({@code SimilarProductQueryService})는 이 결과만 읽고 AI를 직접 호출하지
 * 않는다 — AI 서버 성능/가동 여부가 상품 상세 페이지에 영향을 주지 않게 하려는 것이다.
 * 실제 호출은 {@link SimilarProductCacheScheduler}가 주기적으로(야간)만 한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SimilarProductCacheService {

    /**
     * AI에 요청할 후보 개수. 서빙 시 실시간 판매상태 필터링으로 줄어들 걸 감안한 여유분 —
     * 기존 SQL 폴백 상한({@code ProductService.SIMILAR_PRODUCT_LIMIT})과 맞춘 값이다.
     * pgvector 코사인 조회 하나라 늘려도 비용 차이가 거의 없고, 배치라 지연시간도 문제없다.
     */
    static final int CANDIDATE_K = 20;

    private final AiClient aiClient;
    private final SimilarProductCandidateRepository candidateRepository;

    /**
     * 상품 하나의 캐시를 갱신한다. AI 호출이 실패해도(타임아웃/5xx 등) 예외를 던지지 않고
     * 로그만 남긴다 — 배치가 상품 하나 때문에 통째로 멈추면 안 된다, 다음 배치 때 재시도된다.
     */
    @Transactional
    public void refreshCache(Long productId) {
        SimilarProductAiResponse response;
        try {
            response = aiClient.getSimilarProducts(productId, CANDIDATE_K);
        } catch (Exception e) {
            log.warn("상품 {} 유사 상품 캐시 갱신 실패 - 다음 배치에 재시도", productId, e);
            return;
        }

        candidateRepository.deleteByProductId(productId);

        List<SimilarProductAiResponse.Item> items = response.items();
        if (items == null || items.isEmpty()) {
            // 대상 상품에 AI 임베딩이 아직 없다(워커 미가동 등) — 에러가 아니다. 다음 배치가
            // 다시 시도하고, 그때까지 서빙은 SQL 폴백이 전담한다.
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        List<SimilarProductCandidate> candidates = new ArrayList<>(items.size());
        for (int rank = 0; rank < items.size(); rank++) {
            SimilarProductAiResponse.Item item = items.get(rank);
            candidates.add(SimilarProductCandidate.builder()
                    .productId(productId)
                    .similarProductId(item.productId())
                    .score(item.score())
                    .rank(rank)
                    .computedAt(now)
                    .build());
        }
        candidateRepository.saveAll(candidates);
    }
}
