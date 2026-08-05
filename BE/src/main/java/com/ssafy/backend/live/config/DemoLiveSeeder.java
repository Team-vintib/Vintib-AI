package com.ssafy.backend.live.config;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

// 사업자 데모 계정 2명에게 예정 라이브 2건씩 시드. DemoMemberSeeder(@Order(1)) 이후 실행되게
// @Order(2)를 둔다. 상품 시드(ProductSeeder, @Order(2))와는 서로 의존이 없어 실행 순서가
// 섞여도 무방하다.
@Slf4j
@Component
@RequiredArgsConstructor
@Order(2)
public class DemoLiveSeeder implements ApplicationRunner {

    private record ScheduledLiveSeed(String title, String description, LocalDateTime scheduledAt) {
    }

    private static final List<ScheduledLiveSeed> BUSINESS1_LIVES = List.of(
            new ScheduledLiveSeed(
                    "가을 신상 스트릿 룩 라이브",
                    "이번 주 새로 들어온 스트릿 브랜드 상의·아우터를 라이브로 소개합니다.",
                    LocalDateTime.now().plusDays(2).withHour(20).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "빈티지 아우터 모음전",
                    "가을·겨울 빈티지 아우터 위주로 편성했습니다.",
                    LocalDateTime.now().plusDays(5).withHour(20).withMinute(0).withSecond(0).withNano(0)));

    private static final List<ScheduledLiveSeed> BUSINESS2_LIVES = List.of(
            new ScheduledLiveSeed(
                    "시즌오프 편집샵 라이브",
                    "제주 편집샵 재고 정리 라이브입니다.",
                    LocalDateTime.now().plusDays(3).withHour(21).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "여성 빈티지 원피스 컬렉션",
                    "빈티지 원피스·스커트 위주로 편성했습니다.",
                    LocalDateTime.now().plusDays(6).withHour(21).withMinute(0).withSecond(0).withNano(0)));

    private final MemberRepository memberRepository;
    private final LiveRepository liveRepository;

    @Override
    public void run(ApplicationArguments args) {
        seedLives("vintibb1@gmail.com", BUSINESS1_LIVES);
        seedLives("vintibb2@gmail.com", BUSINESS2_LIVES);
    }

    /** 부족한 예정 라이브만 채운다(멱등) — 이미 만들어 둔 만큼은 건너뛴다. */
    private void seedLives(String hostEmail, List<ScheduledLiveSeed> seeds) {
        Member host = memberRepository.findByEmail(hostEmail).orElse(null);
        if (host == null) {
            log.warn("라이브 시드 대상 회원이 없다: {}", hostEmail);
            return;
        }
        long existing = liveRepository.countByHost_IdAndStatusIn(host.getId(), List.of(LiveStatus.SCHEDULED));
        if (existing >= seeds.size()) {
            return;
        }
        log.info("시드 예정 라이브 생성: {} ({}건)", hostEmail, seeds.size() - existing);
        seeds.stream()
                .skip(existing)
                .forEach(seed -> liveRepository.save(
                        Live.schedule(host, seed.title(), null, seed.description(), seed.scheduledAt())));
    }
}
