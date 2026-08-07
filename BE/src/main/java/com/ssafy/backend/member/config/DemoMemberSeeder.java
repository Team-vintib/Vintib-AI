package com.ssafy.backend.member.config;

import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.repository.PointAccountRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

// 데모/테스트용 고정 계정 시드. 이메일이 이미 존재하면 건너뛰어
// 재기동·재배포 시에도 중복 삽입 없이 항상 로그인 가능한 상태를 유지한다.
// (운영이 ddl-auto: update 라 데이터가 살아남는다 — 이 멱등성이 실제로 필요하다.)
// ProductSeeder(@Order(2))가 이 시드에 의존하므로 @Order(1)로 먼저 실행되게 한다.
@Slf4j
@Component
@RequiredArgsConstructor
@Order(1)
public class DemoMemberSeeder implements ApplicationRunner {

    // 개인 사용자 4명 (GENERAL)
    private static final String[][] GENERAL_USERS = {
        {"vintib1@gmail.com", "qwer1234", "한서윤", "빈티지흙깜자", "FEMALE", "01012321232",
         "서울 강남구 테헤란로 212", "멀티캠퍼스 801호", "06220"},

        {"vintib2@gmail.com", "qwer1234", "김현수", "마좀깎아주라", "FEMALE", "01032123212",
         "부산 동래구 사직로 45", "1층", "47874"},

        {"vintib3@gmail.com","qwer1234", "최형수", "헌옷수거함털이범", "MALE", "01045654565",
         "대전 중구 대종로480번길 15", "2층", "34921"},

        {"vintib4@gmail.com", "qwer1234", "김정윤", "KING받는classic", "MALE", "01078987898",
         "경기 화성시 동탄구 동탄대로9나길 14", "1004호", "18488"},
    };

    // 사업자 2명 (BUSINESS)
    private static final String[][] BUSINESS_USERS = {
        {"vintibb1@gmail.com", "qwer1234", "정인웅", "파는이유살쪄서", "MALE", "01015951595",
         "서울 용산구 녹사평대로 150", "1층", "04390"},

        {"vintibb2@gmail.com", "qwer1234", "김서연", "구제불능", "FEMALE", "01042324232",
         "제주 제주시 첨단로 242", "202호", "63309"},
    };

    // 데모 계정 기본 지급 포인트. 입찰/결제를 바로 테스트할 수 있게 시드 시점에 충전해 둔다.
    private static final long DEFAULT_SEED_POINTS = 1_000_000L;

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;
    private final PointAccountRepository pointAccountRepository;

    @Override
    public void run(ApplicationArguments args) {
        seedGeneralUsers();
        seedBusinessUsers();
    }

    /** 개인 사용자 4명 시드. */
    private void seedGeneralUsers() {
        for (String[] u : GENERAL_USERS) {
            seedMember(u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], MemberType.GENERAL);
        }
    }

    /** 사업자 2명 시드. */
    private void seedBusinessUsers() {
        for (String[] u : BUSINESS_USERS) {
            seedMember(u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], MemberType.BUSINESS);
        }
    }

    /**
     * 이메일이 없으면 회원을 생성하고 온보딩 완료 처리한다. 이미 존재하면 회원 생성은 건너뛴다(멱등).
     * 포인트 지급은 회원 존재 여부와 별개로 계정마다 확인한다 — 이 시드 로직이 나중에 추가돼도
     * 기존에 이미 만들어진 데모 계정에 포인트 계좌를 backfill 할 수 있도록.
     *
     * @param genderStr "MALE" 또는 "FEMALE"
     */
    private void seedMember(
            String email, String password, String name, String nickname,
            String genderStr, String phone, String address, String detailAddress,
            String postalCode, MemberType memberType) {
        Member member = memberRepository.findByEmail(email).orElse(null);
        if (member == null) {
            log.info("시드 계정 생성: {} ({})", email, memberType);
            Gender gender = "FEMALE".equals(genderStr) ? Gender.FEMALE : Gender.MALE;
            member = Member.builder()
                    .email(email)
                    .password(passwordEncoder.encode(password))
                    .name(name)
                    .build();
            member.updateBasicInfo(nickname, phone, address, detailAddress, postalCode, gender);
            member.completeOnboarding(memberType);
            member = memberRepository.save(member);
        }
        seedPoints(member);
    }

    /**
     * 포인트 계좌를 최소 {@link #DEFAULT_SEED_POINTS}까지 채운다(멱등). 계좌가 없으면 새로
     * 만들고, 이미 있는데 기본 지급액보다 적으면(과거 기본값으로 만들어졌거나 테스트로 깎인
     * 경우) 그 차액만큼만 충전한다 — 기본 지급액보다 많이 갖고 있으면(구매·정산 등으로 늘어난
     * 경우) 건드리지 않는다.
     */
    private void seedPoints(Member member) {
        PointAccount account = pointAccountRepository.findById(member.getId()).orElse(null);
        if (account == null) {
            log.info("시드 계정 포인트 지급: {} ({}P)", member.getEmail(), DEFAULT_SEED_POINTS);
            account = PointAccount.builder().member(member).build();
            account.charge(DEFAULT_SEED_POINTS);
            pointAccountRepository.save(account);
            return;
        }
        long shortfall = DEFAULT_SEED_POINTS - account.getAvailable();
        if (shortfall > 0) {
            log.info("시드 계정 포인트 충전: {} (+{}P)", member.getEmail(), shortfall);
            account.charge(shortfall);
            pointAccountRepository.save(account);
        }
    }
}