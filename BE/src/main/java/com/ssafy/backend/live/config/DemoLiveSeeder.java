package com.ssafy.backend.live.config;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.config.DemoPriorityProducts;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.product.service.ProductImageService;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 사업자 데모 계정 2명에게 예정 라이브 2건씩 시드하고, 우선순위 상품(호스트 소유 +
 * {@link DemoPriorityProducts})을 편성까지 해 둔다. 썸네일은 그 방송에 편성된 첫 상품의
 * 대표 이미지를 그대로 쓴다.
 *
 * <p>이제 상품을 편성해야 해서 상품 시드(ProductSeeder, {@code @Order(2)})가 끝난 뒤 실행돼야
 * 한다 — DemoOrderSeeder와 같은 {@code @Order(3)}을 둔다(DemoOrderSeeder와는 서로 의존이 없어
 * 그 안에서의 순서는 무방하다).
 */
@Slf4j
@Component
@RequiredArgsConstructor
@Order(3)
public class DemoLiveSeeder implements ApplicationRunner {

    private record ScheduledLiveSeed(String title, String description, LocalDateTime scheduledAt) {
    }

    // 한 방송에 편성할 우선순위 상품 수.
    private static final int PRODUCTS_PER_LIVE = 3;

    // 이미 다른 방송(SCHEDULED/LIVE)에 걸린 상품은 편성 후보에서 뺀다 — LiveProductService가
    // 실제 연결 시 강제하는 것과 같은 불변식이다.
    private static final Set<LiveStatus> OPEN_STATUSES = Set.of(LiveStatus.SCHEDULED, LiveStatus.LIVE);

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
    private final LiveProductRepository liveProductRepository;
    private final ProductRepository productRepository;
    private final ProductImageService productImageService;

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

        List<Product> candidates = candidateProducts(host.getId());
        int cursor = 0;

        log.info("시드 예정 라이브 생성: {} ({}건)", hostEmail, seeds.size() - existing);
        for (ScheduledLiveSeed seed : seeds.stream().skip(existing).toList()) {
            List<Product> picked = new ArrayList<>();
            while (picked.size() < PRODUCTS_PER_LIVE && cursor < candidates.size()) {
                picked.add(candidates.get(cursor++));
            }
            if (picked.size() < PRODUCTS_PER_LIVE) {
                log.warn("라이브 편성용 우선순위 상품이 부족하다: {} ({}건만 편성)", hostEmail, picked.size());
            }

            String thumbnailUrl = picked.isEmpty() ? null : primaryImageUrl(picked.get(0));
            Live live = liveRepository.save(
                    Live.schedule(host, seed.title(), thumbnailUrl, seed.description(), seed.scheduledAt()));

            LocalDateTime addedAt = LocalDateTime.now();
            short sortOrder = 0;
            for (Product product : picked) {
                liveProductRepository.save(LiveProduct.link(live, product.getId(), sortOrder++, addedAt));
            }
        }
    }

    /** 호스트 소유 + 우선순위 상품 + 편성 가능(DRAFT/SOLD 제외, 다른 열린 방송에 안 걸림), id순. */
    private List<Product> candidateProducts(Long hostId) {
        return productRepository.findAll().stream()
                .filter(product -> product.isOwnedBy(hostId))
                .filter(product -> DemoPriorityProducts.IDS.contains(product.getId()))
                .filter(product -> product.getSaleStatus() != SaleStatus.DRAFT
                        && product.getSaleStatus() != SaleStatus.SOLD)
                .filter(product -> !liveProductRepository.existsByProductIdAndRemovedAtIsNullAndLive_StatusIn(
                        product.getId(), OPEN_STATUSES))
                .sorted(Comparator.comparing(Product::getId))
                .toList();
    }

    private String primaryImageUrl(Product product) {
        return productImageService.getPrimaryImageUrls(List.of(product.getId())).get(product.getId());
    }
}
