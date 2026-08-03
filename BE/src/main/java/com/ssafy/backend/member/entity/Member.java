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
import org.hibernate.annotations.ColumnDefault;

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

    @Column(name = "detail_address")
    private String detailAddress;

    @Column(name = "postal_code", length = 10)
    private String postalCode;

    @Enumerated(EnumType.STRING)
    private Gender gender;

    @Column(nullable = false)
    private boolean onboardingCompleted;

    // 스키마 정합성 보강 (schema.sql 반영) — 기존 FE 요청서(001-member-entity-schema-drift.md) 대응.
    // DB 기본값은 @ColumnDefault로 별도 선언한다 — columnDefinition 문자열에 DEFAULT까지 합쳐 넣으면
    // 컬럼이 이미 존재하는 상태로 재기동할 때마다 Hibernate가 "alter column ... set data type
    // VARCHAR(20) DEFAULT '...'"를 생성하는데, Postgres는 ALTER COLUMN TYPE 절에 DEFAULT를 못 받아
    // 매 부팅마다 문법 오류로 실패한다(기능엔 영향 없지만 로그 노이즈). @ColumnDefault는 별도
    // SET DEFAULT 문으로 나가서 이 문제가 없다.
    @Enumerated(EnumType.STRING)
    @Column(name = "member_type", nullable = false, length = 20)
    @ColumnDefault("'GENERAL'")
    private MemberType memberType = MemberType.GENERAL;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @ColumnDefault("'ACTIVE'")
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
     * ONBOARD-001: 닉네임·전화번호·주소·상세주소·우편번호·성별을 등록한다.
     * MY-001 에서 이후에도 동일 메서드로 수정할 수 있다. 우편번호를 제외한 나머지는 전부 필수 입력이다
     * (컨트롤러의 Bean Validation에서 이미 걸러진다). 우편번호는 주소 검색을 안 쓰고 직접 입력하면
     * null일 수 있다. 온보딩 최종 완료 처리는 이 메서드가 아니라 ONBOARD-004({@link #completeOnboarding})
     * 시점에 이뤄진다(SY021).
     */
    public void updateBasicInfo(
            String nickname,
            String phoneNumber,
            String address,
            String detailAddress,
            String postalCode,
            Gender gender) {
        this.nickname = nickname;
        this.phoneNumber = phoneNumber;
        this.address = address;
        this.detailAddress = detailAddress;
        this.postalCode = postalCode;
        this.gender = gender;
    }

    /**
     * ONBOARD-004: 회원 유형(일반/사업자)을 저장하고 온보딩을 최종 완료 처리한다.
     * 이미 완료한 회원이 다시 호출해도 유형만 갱신하고 성공 처리한다(멱등).
     */
    public void completeOnboarding(MemberType memberType) {
        this.memberType = memberType;
        this.onboardingCompleted = true;
    }
}