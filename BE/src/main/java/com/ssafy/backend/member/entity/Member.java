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

    @Column(nullable = false)
    private String password;

    @Column(nullable = false)
    private String name;

    // 온보딩 단계에서 채워지는 정보 (가입 시점에는 null)
    private String nickname;

    private String phoneNumber;

    private String address;

    @Enumerated(EnumType.STRING)
    private Gender gender;

    @Column(nullable = false)
    private boolean onboardingCompleted;

    @Builder
    public Member(String email, String password, String name) {
        this.email = email;
        this.password = password;
        this.name = name;
        this.onboardingCompleted = false;
    }

    public void completeOnboarding(String nickname, String phoneNumber, String address, Gender gender) {
        this.nickname = nickname;
        this.phoneNumber = phoneNumber;
        this.address = address;
        this.gender = gender;
        this.onboardingCompleted = true;
    }
}