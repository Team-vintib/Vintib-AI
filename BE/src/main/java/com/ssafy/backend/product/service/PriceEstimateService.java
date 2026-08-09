package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.PricingEstimateJobRequest;
import com.ssafy.backend.product.dto.request.PriceEstimateRequest;
import com.ssafy.backend.product.dto.response.PriceEstimateJobResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/**
 * 상품 등록 화면 "AI 가격 추천" 경량 트리거(044) — {@code POST /pricing/estimates}를 그대로
 * 프록시한다. 결과 폴링({@code GET /ai/jobs/{jobId}})은 FE가 외부 경로로 직접 하므로
 * (품질 검증과 같은 방식), BE는 job 접수까지만 책임진다.
 *
 * <p>AI가 동시 처리 상한(2건)을 넘겨 503을 내면 예외가 그대로 컨트롤러까지 전파된다 — 재시도는
 * 하지 않는다. FE가 등급별로 나눠 호출하는 쪽에서 그 상한을 이미 고려하고 있다.
 */
@Service
@RequiredArgsConstructor
public class PriceEstimateService {

    // AI 쪽 product_id는 에코 전용이지만 ge=1 제약이 걸려 있어(PricingRequest.product_id) 0을
    // 못 쓴다 — 아직 생성되지 않은 상품에 쓰는 placeholder.
    private static final long PLACEHOLDER_PRODUCT_ID = 1L;

    private final AiClient aiClient;
    private final GarmentCategoryMapper garmentCategoryMapper;

    public PriceEstimateJobResponse createEstimateJob(PriceEstimateRequest request) {
        String category = garmentCategoryMapper.resolve(request.categoryId()).orElse(null);
        long productId = request.productId() != null ? request.productId() : PLACEHOLDER_PRODUCT_ID;

        String jobId = aiClient.createPricingEstimateJob(new PricingEstimateJobRequest(
                productId,
                request.productName(),
                request.brand(),
                category,
                request.categoryId(),
                request.conditionScore(),
                request.conditionGrade()));

        return new PriceEstimateJobResponse(jobId);
    }
}