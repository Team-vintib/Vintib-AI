package com.ssafy.backend.member.config;

import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

// 데모/테스트용 고정 계정 시드(S15P11A108-448). 이메일이 이미 존재하면 건너뛰어
// 재기동·재배포(ddl-auto: create) 시에도 중복 삽입 없이 항상 로그인 가능한 상태를 유지한다.
@Slf4j
@Component
@RequiredArgsConstructor
public class DemoMemberSeeder implements ApplicationRunner {

    private static final String DEMO_EMAIL = "vintib_user@naver.com";
    private static final String DEMO_PASSWORD = "a108a108";
    private static final String DEMO_NAME = "Vintib Tester";
    private static final String DEMO_NICKNAME = "vintib_tester";

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(ApplicationArguments args) {
        if (memberRepository.existsByEmail(DEMO_EMAIL)) {
            return;
        }

        log.info("데모 계정 시드를 실행합니다: {}", DEMO_EMAIL);
        Member member = Member.builder()
                .email(DEMO_EMAIL)
                .password(passwordEncoder.encode(DEMO_PASSWORD))
                .name(DEMO_NAME)
                .build();
        // SY019 게이트: 온보딩 미완료면 데모 계정으로도 다른 기능을 못 쓰게 되므로 완료 상태로 시드한다.
        member.updateBasicInfo(DEMO_NICKNAME, "01000000000", "서울특별시", "1층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        memberRepository.save(member);
    }
}
