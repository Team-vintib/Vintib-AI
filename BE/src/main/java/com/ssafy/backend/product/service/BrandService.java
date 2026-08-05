package com.ssafy.backend.product.service;

import com.ssafy.backend.product.dto.response.BrandResponse;
import com.ssafy.backend.product.repository.BrandRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class BrandService {

    private final BrandRepository brandRepository;

    public List<BrandResponse> getAllBrands() {
        return brandRepository.findAllByOrderByNameAsc().stream()
                .map(BrandResponse::from)
                .toList();
    }
}
