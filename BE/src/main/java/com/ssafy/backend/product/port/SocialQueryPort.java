package com.ssafy.backend.product.port;

public interface SocialQueryPort {
    
    boolean isWishedBy(Long productId, Long memberId);
    
    long countFollowers(Long sellerId);
}
