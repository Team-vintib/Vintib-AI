package com.ssafy.backend.product.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.product.dto.response.ProductAiModelCutResponse;
import com.ssafy.backend.product.dto.response.ProductQualityInspectionResponse;
import com.ssafy.backend.product.entity.AiModelCutStatus;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.QualityInspectionStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

/** AI 착용컷·하자 검수 job 상태 조회. 안 끝난 job이면 조회하는 시점에 AI를 다시 찔러 최신 상태를 반영하는 "지연 폴링" 방식. */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductAiJobStatusService {

    private final ProductRepository productRepository;
    private final AiClient aiClient;

    @Transactional
    public ProductAiModelCutResponse getAiModelCutStatus(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (product.getAiModelCutStatus() == AiModelCutStatus.PENDING
                || product.getAiModelCutStatus() == AiModelCutStatus.PROCESSING) {
            refreshAiModelCutStatus(product);
        }

        return ProductAiModelCutResponse.from(product);
    }

    private void refreshAiModelCutStatus(Product product) {
        try {
            AiJobResponse job = aiClient.getJob(product.getAiModelCutJobId());
            if (job.isSuccess()) {
                Object imageUrl = job.result() != null ? job.result().get("image_url") : null;
                if (imageUrl != null) {
                    product.completeAiModelCutJob(imageUrl.toString());
                } else {
                    product.failAiModelCutJob();
                }
            } else if (job.isFailed()) {
                product.failAiModelCutJob();
            } else if ("processing".equals(job.status())) {
                product.markAiModelCutProcessing();
            }
            // queued -> PENDING 그대로 둔다.
        } catch (RestClientException e) {
            // 일시적 네트워크 오류. FAILED로 단정하지 않고 다음 폴링에서 재시도.
            log.warn(
                    "AI 착용컷 job 상태 조회 실패(productId={}, jobId={}): {}",
                    product.getId(), product.getAiModelCutJobId(), e.getMessage());
        }
    }

    /**
     * 하자 검수 상태/결과를 조회.
     * BE가 이 엔드포인트에서 아직 안 끝난 job이면 조회 시점에 AI를 조회해 최신화. (FE가 직접 폴링 x).
     */
    @Transactional
    public ProductQualityInspectionResponse getQualityInspectionStatus(Long productId) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        if (product.getQualityInspectionStatus() == QualityInspectionStatus.PENDING
                || product.getQualityInspectionStatus() == QualityInspectionStatus.PROCESSING) {
            refreshQualityInspectionStatus(product);
        }

        return ProductQualityInspectionResponse.from(product);
    }

    private void refreshQualityInspectionStatus(Product product) {
        try {
            AiJobResponse job = aiClient.getJob(product.getQualityInspectionJobId());
            if (job.isSuccess()) {
                if (job.result() != null) {
                    product.completeQualityInspectionJob(job.result());
                } else {
                    product.failQualityInspectionJob();
                }
            } else if (job.isFailed()) {
                product.failQualityInspectionJob();
            } else if ("processing".equals(job.status())) {
                product.markQualityInspectionProcessing();
            }
            // queued -> PENDING 그대로.
        } catch (RestClientException e) {
            // 일시적 네트워크 오류. FAILED로 단정하지 않고 다음 폴링에서 재시도.
            log.warn(
                    "하자 검수 job 상태 조회 실패(productId={}, jobId={}): {}",
                    product.getId(), product.getQualityInspectionJobId(), e.getMessage());
        }
    }
}