package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.service.LiveViewerService;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * 라이브 목록을 홈/팔로잉 카드로 조립한다. {@link ProductCardAssembler}와 같은 이유로 한 곳에 둔다.
 *
 * <p>시청자 수는 DB가 아니라 Redis 집계에서 온다. 라이브마다 따로 물으면 카드 수만큼 왕복하므로
 * {@link LiveViewerService#getViewerCounts}로 한 번에 받는다. 편성 상품 수도 마찬가지다.
 */
@Component
@RequiredArgsConstructor
public class LiveCardAssembler {

    private final LiveProductRepository liveProductRepository;
    private final LiveViewerService liveViewerService;

    public List<LiveCardResponse> toCards(List<Live> lives) {
        if (lives.isEmpty()) {
            return List.of();
        }

        List<Long> liveIds = lives.stream().map(Live::getId).toList();
        Map<Long, Integer> viewerCounts = liveViewerService.getViewerCounts(liveIds);
        Map<Long, Long> productCounts = liveProductRepository.findByLiveIdInAndRemovedAtIsNull(liveIds).stream()
                .collect(Collectors.groupingBy(
                        liveProduct -> liveProduct.getLive().getId(),
                        Collectors.counting()));

        return lives.stream()
                .map(live -> LiveCardResponse.of(
                        live,
                        viewerCounts.getOrDefault(live.getId(), 0),
                        productCounts.getOrDefault(live.getId(), 0L).intValue()))
                .toList();
    }
}
