package com.ssafy.backend.live.config;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
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
 *
 * <p><b>썸네일은 전용 이미지를 쓴다.</b> 상품 이미지에서 유도하던 이전 방식 대신, 라이브
 * 전용으로 {@code vintib-public/live/live (1).jpg} ~ {@code live (4).jpg} 4장을 수동
 * 업로드해 두고 그 키만 문자열로 채운다({@code docs/sync-images-to-prod.md}의 products 업로드
 * 절차와 같은 방식, 폴더만 {@code live/}). {@code LiveProduct} 레코드를 만들지 않으므로 위
 * 편성 충돌과는 무관하다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@Order(3)
public class DemoLiveSeeder implements ApplicationRunner {

    private record ScheduledLiveSeed(String title, String description, LocalDateTime scheduledAt) {
    }

    private static final String THUMBNAIL_FOLDER = "live";

    // 예약 시각은 전부 지금부터 2일 이내로 잡는다 — "곧 열릴 방송"으로 보이게.
    private static final List<ScheduledLiveSeed> BUSINESS1_LIVES = List.of(
            new ScheduledLiveSeed(
                    "시즌오프 편집샵 라이브",
                    "제주 편집샵 재고 정리 라이브 진행합니다 !! 🍊",
                    LocalDateTime.now().plusDays(1).withHour(20).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "숲속의 옷장: 모리걸 룩북",
                    "모리걸 스타일의 귀여운 빈티지 스타일을 소개해요. 🌲🌳",
                    LocalDateTime.now().plusDays(2).withHour(20).withMinute(0).withSecond(0).withNano(0)));

    private static final List<ScheduledLiveSeed> BUSINESS2_LIVES = List.of(
            new ScheduledLiveSeed(
                    "시즌오프 편집샵 라이브",
                    "가을 신상 라이브 ♥️ 스트릿하면서도 빈티지한 룩북 추천해드려요 😎😎`",
                    LocalDateTime.now().plusDays(1).withHour(21).withMinute(0).withSecond(0).withNano(0)),
            new ScheduledLiveSeed(
                    "여성 빈   티지 원피스 컬렉션",
                    "빈티지 원피스·스커트 위주로 보여드립니다 ! 여신 누나들 예약해두기 💙💙",
                    LocalDateTime.now().plusDays(2).withHour(21).withMinute(0).withSecond(0).withNano(0)));

    // BUSINESS1_LIVES[0]→live (1).jpg, [1]→live (2).jpg, BUSINESS2_LIVES[0]→live (3).jpg, [1]→live (4).jpg.
    private static final List<String> BUSINESS1_THUMBNAILS = List.of("live (1).jpg", "live (2).jpg");
    private static final List<String> BUSINESS2_THUMBNAILS = List.of("live (3).jpg", "live (4).jpg");

    private final MemberRepository memberRepository;
    private final LiveRepository liveRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        seedLives("vintibb1@gmail.com", BUSINESS1_LIVES, BUSINESS1_THUMBNAILS);
        seedLives("vintibb2@gmail.com", BUSINESS2_LIVES, BUSINESS2_THUMBNAILS);
    }

    /** 부족한 예정 라이브만 채운다(멱등) — 이미 만들어 둔 만큼은 건너뛴다. */
    private void seedLives(String hostEmail, List<ScheduledLiveSeed> seeds, List<String> thumbnailFileNames) {
        Member host = memberRepository.findByEmail(hostEmail).orElse(null);
        if (host == null) {
            log.warn("라이브 시드 대상 회원이 없다: {}", hostEmail);
            return;
        }
        long existing = liveRepository.countByHost_IdAndStatusIn(host.getId(), List.of(LiveStatus.SCHEDULED));
        if (existing >= seeds.size()) {
            return;
        }

        String bucket = awsProperties.s3().publicBucket();
        log.info("시드 예정 라이브 생성: {} ({}건)", hostEmail, seeds.size() - existing);
        for (int i = (int) existing; i < seeds.size(); i++) {
            ScheduledLiveSeed seed = seeds.get(i);
            String thumbnailUrl = s3StorageService.publicUrl(bucket, THUMBNAIL_FOLDER + "/" + thumbnailFileNames.get(i));
            liveRepository.save(
                    Live.schedule(host, seed.title(), thumbnailUrl, seed.description(), seed.scheduledAt()));
        }
    }
}
