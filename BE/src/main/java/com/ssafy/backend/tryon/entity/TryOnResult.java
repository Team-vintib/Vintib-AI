package com.ssafy.backend.tryon.entity;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "tryon_result")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class TryOnResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    // saveResult()의 레거시 경로(이미 생성된 바이트를 직접 저장)에서만 쓴다 — BE 자체
    // private 버킷의 S3 key다.
    @Column(name = "image_key", length = 500)
    private String imageKey;

    // job 경로(createResult)에서 완료 시 채운다 — AI 게이트웨이가 돌려준 결과 이미지 URL을
    // 그대로 저장한다(BE S3에 재업로드하지 않는다, MVP 범위). imageKey와 둘 중 하나만 채워진다.
    @Column(name = "result_image_url", length = 500)
    private String resultImageUrl;

    @Column(name = "job_id", length = 100)
    private String jobId;

    // 필드 기본값이 아니라 두 호출부(saveResult=SUCCESS, createResult=PENDING)가 항상 명시적으로
    // 지정한다 — @Builder가 생성자를 그대로 쓰므로 필드 이니셜라이저는 여기서 의미가 없다.
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 10)
    private TryOnResultStatus status;

    // "한 줄 핏 예상" (docs/requests/BE/038-tryon-fit-summary-fields.md). 둘 다 null일 수 있다
    // (회원 신체 실측·상품 실측이 부족하면 AI가 계산을 못 한다).
    @Column(name = "fit_title", length = 100)
    private String fitTitle;

    @Column(name = "fit_description", length = 300)
    private String fitDescription;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @Builder
    private TryOnResult(
            Member member, Product product, String imageKey, String jobId, TryOnResultStatus status) {
        this.member = member;
        this.product = product;
        this.imageKey = imageKey;
        this.jobId = jobId;
        this.status = status;
        this.createdAt = LocalDateTime.now();
    }

    public boolean isOwnedBy(Long memberId) {
        return memberId != null && member.getId().equals(memberId);
    }

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }

    public boolean isPending() {
        return status == TryOnResultStatus.PENDING || status == TryOnResultStatus.PROCESSING;
    }

    public void markProcessing() {
        this.status = TryOnResultStatus.PROCESSING;
    }

    public void complete(String resultImageUrl, String fitTitle, String fitDescription) {
        this.resultImageUrl = resultImageUrl;
        this.fitTitle = fitTitle;
        this.fitDescription = fitDescription;
        this.status = TryOnResultStatus.SUCCESS;
    }

    public void fail() {
        this.status = TryOnResultStatus.FAILED;
    }
}