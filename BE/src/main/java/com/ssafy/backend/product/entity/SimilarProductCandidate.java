package com.ssafy.backend.product.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * AI CLIP 임베딩 유사도 배치 사전계산 결과 캐시(CH034).
 *
 * <p>{@code SimilarProductCacheScheduler}가 주기적으로(야간) 채우고, 서빙 경로
 * ({@code SimilarProductQueryService})는 이 테이블만 읽는다 — AI를 실시간 호출하지 않아
 * AI 서버 성능/가동 여부가 상품 상세 페이지에 영향을 주지 않는다.
 *
 * <p>상품 하나({@code productId})당 배치가 요청한 만큼(최대 20행)만 유지한다. 배치가 돌
 * 때마다 그 상품의 기존 행을 전부 지우고 새로 넣는다(upsert-by-replace) — 순위가 바뀌면
 * 낡은 행이 남을 이유가 없다.
 */
@Entity
@Table(
        name = "similar_product_candidate",
        indexes = {@Index(name = "idx_similar_product_candidate_product_id", columnList = "product_id")})
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimilarProductCandidate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "similar_product_id", nullable = false)
    private Long similarProductId;

    @Column(nullable = false)
    private Double score;

    // 0부터 시작 — AI 응답 순서(코사인 유사도 내림차순) 그대로. 서빙 시 이 순서로 읽는다.
    @Column(nullable = false)
    private Integer rank;

    @Column(name = "computed_at", nullable = false)
    private LocalDateTime computedAt;

    @Builder
    private SimilarProductCandidate(
            Long productId, Long similarProductId, Double score, Integer rank, LocalDateTime computedAt) {
        this.productId = productId;
        this.similarProductId = similarProductId;
        this.score = score;
        this.rank = rank;
        this.computedAt = computedAt;
    }
}
