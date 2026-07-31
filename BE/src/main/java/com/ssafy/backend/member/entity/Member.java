package com.ssafy.backend.member.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "member")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Member extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    // SSO 전용 계정은 null 허용 (AUTH-003)
    @Column
    private String password;

    @Column(nullable = false)
    private String name;

    // 온보딩 단계에서 채워지는 정보 (가입 시점에는 null)
    // nickname 은 unique 제약만 두고 NOT NULL 은 달지 않는다.
    // 온보딩 완료 전에는 null 상태이고, 온보딩 완료 시 서비스 레이어에서 필수 검증한다.
    @Column(unique = true)
    private String nickname;

    @Column(name = "phone_number")
    private String phoneNumber;

    private String address;

    @Enumerated(EnumType.STRING)
    private Gender gender;

    @Column(nullable = false)
    private boolean onboardingCompleted;

    // 스키마 정합성 보강 (schema.sql 반영) — 기존 FE 요청서(001-member-entity-schema-drift.md) 대응
    // columnDefinition에 DEFAULT를 명시한다 — 이미 row가 쌓인 테이블에 NOT NULL 컬럼을 ddl-auto=update로
    // 추가할 때 DEFAULT가 없으면 기존 row가 제약을 위반해 ALTER TABLE 자체가 실패한다.
    @Enumerated(EnumType.STRING)
    @Column(name = "member_type", nullable = false, columnDefinition = "VARCHAR(20) DEFAULT 'GENERAL'")
    private MemberType memberType = MemberType.GENERAL;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "VARCHAR(20) DEFAULT 'ACTIVE'")
    private MemberStatus status = MemberStatus.ACTIVE;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @Column(name = "profile_image_url", length = 500)
    private String profileImageUrl;

    @Builder
    public Member(String email, String password, String name) {
        this.email = email;
        this.password = password;
        this.name = name;
        this.onboardingCompleted = false;
        this.memberType = MemberType.GENERAL;
        this.status = MemberStatus.ACTIVE;
    }

    /**
     * ONBOARD-001: 닉네임·전화번호·주소·성별을 등록하고 온보딩 완료 처리한다.
     * MY-001 에서 이후에도 동일 메서드로 수정할 수 있다.
     */
    public void updateBasicInfo(String nickname, String phoneNumber, String address, Gender gender) {
        this.nickname = nickname;
        this.phoneNumber = phoneNumber;
        this.address = address;
        // 성별은 선택 입력이다 — null로 보내면 마이페이지 수정(MY-001)에서 기존 값을 지우지 않고 유지한다.
        if (gender != null) {
            this.gender = gender;
        }
        this.onboardingCompleted = true;
    }

    /** @deprecated onboardingCompleted 플래그를 직접 쓰는 코드가 없도록 이 메서드만 남긴다. */
    public void completeOnboarding(String nickname, String phoneNumber, String address, Gender gender) {
        updateBasicInfo(nickname, phoneNumber, address, gender);
    }
}