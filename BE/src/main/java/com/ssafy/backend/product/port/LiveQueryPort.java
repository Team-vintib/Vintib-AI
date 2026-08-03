package com.ssafy.backend.product.port;

import com.ssafy.backend.product.port.dto.LinkedLiveSummary;
import java.util.Optional;

public interface LiveQueryPort {
    
    Optional<LinkedLiveSummary> findLinkedLive(Long productId);
}
