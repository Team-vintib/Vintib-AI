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
import org.springframework.transaction.annotation.Transactional;

/**
 * 사업자 데모 계정 2명에게 예정 라이브 2건씩 시드한다.
 *
 * <p><b>상품은 편성하지 않는다.</b> 예전에는 우선순위 상품을 자동 편성했는데, 이 시더가
 * {@code @Profile} 가드 없이 운영에도 그대로 돌아 데모 계정이 실제로 라이브를 열 때
 * 우선순위 상품이 이미 걸려 있어 {@code PRODUCT_ALREADY_LINKED}(409)가 나는 문제가 있었다.
 * 상품 편성은 각 계정이 API로 직접 하도록 비워 둔다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@Order(3)
public class DemoLiveSeeder implements ApplicationRunner {

    private record ScheduledLiveSeed(String title, String description, LocalDateTime scheduledAt) {
    }

    // 예약 시각은 전부 지금부터 2일 이내로 잡는다 — "곧 열릴 방송"으로 보이게.
    private static final List<ScheduledLiveSeed> BUSINESS1_LIVES = List.of(
            new ScheduledLiveSeed(
                    "가을 신상 스트릿 룩 라이브",
                    "이번 주 새로 들어온 스트릿 브랜드 상의·아우터를 라이브로 소개합니다.",
                    LocalDateTime.now().plusDays(1).withHour(20).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "빈티지 아우터 모음전",
                    "가을·겨울 빈티지 아우터 위주로 편성했습니다.",
                    LocalDateTime.now().plusDays(2).withHour(20).withMinute(0).withSecond(0).withNano(0)));

    private static final List<ScheduledLiveSeed> BUSINESS2_LIVES = List.of(
            new ScheduledLiveSeed(
                    "시즌오프 편집샵 라이브",
                    "제주 편집샵 재고 정리 라이브입니다.",
                    LocalDateTime.now().plusDays(1).withHour(21).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "여성 빈티지 원피스 컬렉션",
                    "빈티지 원피스·스커트 위주로 편성했습니다.",
                    LocalDateTime.now().plusDays(2).withHour(21).withMinute(0).withSecond(0).withNano(0)));

    private final MemberRepository memberRepository;
    private final LiveRepository liveRepository;

    @Override
    @Transactional
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
        for (ScheduledLiveSeed seed : seeds.stream().skip(existing).toList()) {
            liveRepository.save(Live.schedule(host, seed.title(), null, seed.description(), seed.scheduledAt()));
        }
    }
}
