package com.ssafy.backend.member.config;

import com.ssafy.backend.member.entity.Member;
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
        memberRepository.save(member);
    }
}
