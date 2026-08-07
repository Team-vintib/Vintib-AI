package com.ssafy.backend.social.config;

import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.social.repository.FollowRepository;
import com.ssafy.backend.social.service.FollowService;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 데모 계정 6명 사이의 팔로우 관계 시드. {@code DemoMemberSeeder}({@code @Order(1)}) 이후 실행되면
 * 되고 상품/라이브와는 의존이 없어 {@code ProductSeeder}/{@code DemoLiveSeeder}와 같은
 * {@code @Order(2)}를 쓴다.
 *
 * <p>고정 간선 목록을 그대로 {@link FollowService#follow}에 태운다 — 자기 자신 팔로우 방지·중복
 * 방지(멱등)를 서비스가 이미 갖고 있어 엔티티를 직접 만들 이유가 없다(주문 시드와 달리 포인트
 * 등 우회해야 할 부수 효과가 없다).
 *
 * <p><b>일부러 비대칭·불균등하게 짰다</b> — 맞팔 쌍도 있고 짝사랑도 있고, 팔로워가 아예 없는
 * 계정도 남겨서 프로필 화면의 팔로워/팔로잉 수 표시가 전부 그럴싸한 숫자 하나로 획일화되지
 * 않게 했다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@Order(2)
public class DemoFollowSeeder implements ApplicationRunner {

    // (팔로워, 팔로잉) — vintibb1은 5명 전원에게 팔로우받는 인기 판매자, vintib3/vintib4는
    // 팔로워가 0명, vintib1↔vintib2·vintibb1↔vintibb2는 맞팔.
    private static final List<String[]> FOLLOW_EDGES = List.of(
            new String[] {"vintib1@gmail.com", "vintibb1@gmail.com"},
            new String[] {"vintib1@gmail.com", "vintibb2@gmail.com"},
            new String[] {"vintib1@gmail.com", "vintib2@gmail.com"},
            new String[] {"vintib2@gmail.com", "vintibb1@gmail.com"},
            new String[] {"vintib2@gmail.com", "vintib1@gmail.com"},
            new String[] {"vintib3@gmail.com", "vintibb1@gmail.com"},
            new String[] {"vintib3@gmail.com", "vintib1@gmail.com"},
            new String[] {"vintib4@gmail.com", "vintibb1@gmail.com"},
            new String[] {"vintib4@gmail.com", "vintibb2@gmail.com"},
            new String[] {"vintib4@gmail.com", "vintib2@gmail.com"},
            new String[] {"vintibb1@gmail.com", "vintibb2@gmail.com"},
            new String[] {"vintibb2@gmail.com", "vintibb1@gmail.com"});

    private final MemberRepository memberRepository;
    private final FollowRepository followRepository;
    private final FollowService followService;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        int created = 0;
        for (String[] edge : FOLLOW_EDGES) {
            if (seedFollow(edge[0], edge[1])) {
                created++;
            }
        }
        if (created > 0) {
            log.info("시드 팔로우 관계 생성: {}건", created);
        }
    }

    /** @return 새로 만들었으면 true, 이미 있었거나 대상 회원이 없어 건너뛰었으면 false */
    private boolean seedFollow(String followerEmail, String followingEmail) {
        Long followerId = memberRepository.findByEmail(followerEmail).map(m -> m.getId()).orElse(null);
        Long followingId = memberRepository.findByEmail(followingEmail).map(m -> m.getId()).orElse(null);
        if (followerId == null || followingId == null) {
            log.warn("팔로우 시드 대상 회원이 없다: {} -> {}", followerEmail, followingEmail);
            return false;
        }
        if (followRepository.existsByFollower_IdAndFollowing_Id(followerId, followingId)) {
            return false;
        }
        followService.follow(followerId, followingId);
        return true;
    }
}
