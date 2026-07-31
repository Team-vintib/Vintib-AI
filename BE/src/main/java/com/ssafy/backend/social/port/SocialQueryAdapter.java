package com.ssafy.backend.social.port;

import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.social.entity.WishId;
import com.ssafy.backend.social.repository.FollowRepository;
import com.ssafy.backend.social.repository.WishRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class SocialQueryAdapter implements SocialQueryPort {

    private final WishRepository wishRepository;
    private final FollowRepository followRepository;

    @Override
    public boolean isWishedBy(Long productId, Long memberId) {
        if (memberId == null) {
            return false;
        }
        return wishRepository.existsById(new WishId(memberId, productId));
    }

    @Override
    public long countFollowers(Long sellerId) {
        return followRepository.countByFollowing_Id(sellerId);
    }
}
