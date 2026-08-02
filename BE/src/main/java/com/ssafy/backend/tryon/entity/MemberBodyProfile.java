package com.ssafy.backend.tryon.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
 * 온보딩(ONBOARD-003)·라이브 시착 패널에서 참조하는 회원의 전신 사진·신체 정보.
 * {@code business_info}와 같은 공유 PK 1:1 구조 — 회원당 한 행만 존재한다(등록=수정=upsert).
 *
 * <p>{@code tryon_result}와 달리 {@code deleted_at}이 없다 — 히스토리 개념이 없는 "현재 상태"
 * 단일 행이라 삭제는 하드 삭제로 처리한다.
 */
@Entity
@Table(name = "member_body_profile")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class MemberBodyProfile {

    @Id
    private Long memberId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id")
    private Member member;

    // 비공개 버킷에 저장되는 S3 key. presigned GET으로만 열 수 있어 고정 URL이 아니라
    // key를 저장한다 — tryon_result.image_key와 동일한 이유.
    @Column(name = "body_photo_key", length = 500)
    private String bodyPhotoKey;

    @Column(name = "height_cm")
    private Short heightCm;

    @Column(name = "weight_kg")
    private Short weightKg;

    @Column(name = "chest_cm")
    private Short chest;

    @Column(name = "waist_cm")
    private Short waist;

    @Column(name = "hip_cm")
    private Short hip;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Builder
    private MemberBodyProfile(Member member) {
        this.member = member;
        this.updatedAt = LocalDateTime.now();
    }

    public void updatePhoto(String bodyPhotoKey) {
        this.bodyPhotoKey = bodyPhotoKey;
        this.updatedAt = LocalDateTime.now();
    }

    /** 인자가 null이면 기존 값을 유지한다 — 온보딩·라이브 패널에서 나눠서 입력해도 이전 값이 지워지지 않게 하기 위함. */
    public void mergeMeasurements(Short heightCm, Short weightKg, Short chest, Short waist, Short hip) {
        if (heightCm != null) {
            this.heightCm = heightCm;
        }
        if (weightKg != null) {
            this.weightKg = weightKg;
        }
        if (chest != null) {
            this.chest = chest;
        }
        if (waist != null) {
            this.waist = waist;
        }
        if (hip != null) {
            this.hip = hip;
        }
        this.updatedAt = LocalDateTime.now();
    }
}
