package com.ssafy.backend.live.port;

import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.product.port.LiveQueryPort;
import com.ssafy.backend.product.port.dto.LinkedLiveSummary;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class LiveQueryAdapter implements LiveQueryPort {

    private final LiveProductRepository liveProductRepository;

    @Override
    public Optional<LinkedLiveSummary> findLinkedLive(Long productId) {
        return liveProductRepository.findByProductIdAndRemovedAtIsNull(productId)
            .map(liveProduct -> {
                var live = liveProduct.getLive();
                return LinkedLiveSummary.builder()
                    .liveId(live.getId())
                    .title(live.getTitle())
                    .status(live.getStatus().name())
                    .scheduledAt(live.getScheduledAt())
                    .startedAt(live.getStartedAt())
                    .thumbnailUrl(live.getThumbnailUrl())
                    .build();
            });
    }
}
