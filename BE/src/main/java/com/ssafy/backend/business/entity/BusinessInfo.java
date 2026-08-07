package com.ssafy.backend.business.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapsId;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 사업자 인증 정보(BIZ-001). {@code member_body_profile}과 같은 공유 PK 1:1 구조 —
 * 회원당 한 행만 존재한다.
 *
 * <p>관리자 승인/거절 플로우는 이번 범위 밖이라, 최초 제출은 항상 {@link BusinessVerificationStatus#PENDING}이고
 * {@code REJECTED} 상태에서만 {@link #resubmit}으로 재제출할 수 있다.
 */
@Entity
@Table(name = "business_info")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessInfo {

    @Id
    private Long memberId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id")
    private Member member;

    @Column(name = "business_number", nullable = false, length = 20)
    private String businessNumber;

    @Column(name = "business_name", nullable = false, length = 100)
    private String businessName;

    @Column(name = "representative_name", nullable = false, length = 50)
    private String representativeName;

    // 비공개 버킷에 저장되는 S3 key. presigned GET으로만 열 수 있어 고정 URL이 아니라
    // key를 저장한다 — member_body_profile.body_photo_key와 동일한 이유.
    @Column(name = "certificate_key", nullable = false, length = 500)
    private String certificateKey;

    @Enumerated(EnumType.STRING)
    @Column(name = "verification_status", nullable = false, length = 20)
    private BusinessVerificationStatus verificationStatus;

    @Column(name = "submitted_at", nullable = false)
    private LocalDateTime submittedAt;

    @Column(name = "verified_at")
    private LocalDateTime verifiedAt;

    @Builder
    private BusinessInfo(
            Member member, String businessNumber, String businessName, String representativeName, String certificateKey) {
        this.member = member;
        this.businessNumber = businessNumber;
        this.businessName = businessName;
        this.representativeName = representativeName;
        this.certificateKey = certificateKey;
        this.verificationStatus = BusinessVerificationStatus.PENDING;
        this.submittedAt = LocalDateTime.now();
    }

    /** REJECTED 상태에서만 서비스가 호출한다 — 상태를 PENDING으로 되돌리고 승인 이력을 초기화한다. */
    public void resubmit(String businessNumber, String businessName, String representativeName, String certificateKey) {
        this.businessNumber = businessNumber;
        this.businessName = businessName;
        this.representativeName = representativeName;
        this.certificateKey = certificateKey;
        this.verificationStatus = BusinessVerificationStatus.PENDING;
        this.submittedAt = LocalDateTime.now();
        this.verifiedAt = null;
    }

    /**
     * 관리자 승인. 관리자 승인 API가 아직 없어(클래스 설명 참고) 지금은 시드 데이터 전용으로만
     * 호출된다 — 실제 승인 플로우가 생기면 그 서비스가 이 메서드를 그대로 재사용하면 된다.
     */
    public void approve() {
        this.verificationStatus = BusinessVerificationStatus.APPROVED;
        this.verifiedAt = LocalDateTime.now();
    }
}