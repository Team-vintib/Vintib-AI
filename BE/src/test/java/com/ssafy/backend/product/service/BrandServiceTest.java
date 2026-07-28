package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.ssafy.backend.product.dto.response.BrandResponse;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.repository.BrandRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class BrandServiceTest {

    @Mock
    private BrandRepository brandRepository;

    @Mock
    private Brand nike;

    private BrandService brandService;

    @BeforeEach
    void setUp() {
        brandService = new BrandService(brandRepository);
    }

    @Test
    void 전체_브랜드_목록을_name_오름차순으로_반환한다() {
        when(nike.getId()).thenReturn(1L);
        when(nike.getName()).thenReturn("나이키");
        when(nike.getNameEn()).thenReturn("Nike");
        when(brandRepository.findAllByOrderByNameAsc()).thenReturn(List.of(nike));

        List<BrandResponse> responses = brandService.getAllBrands();

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).name()).isEqualTo("나이키");
        assertThat(responses.get(0).nameEn()).isEqualTo("Nike");
    }
}
