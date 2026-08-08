package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class GarmentCategoryMapperTest {

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private Category category;

    private GarmentCategoryMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = new GarmentCategoryMapper(categoryRepository);
    }

    @Test
    void 매핑되는_카테고리는_GarmentCategory를_반환한다() {
        when(categoryRepository.findById(1L)).thenReturn(Optional.of(category));
        when(category.getNameEn()).thenReturn("KNIT");

        assertThat(mapper.resolve(1L)).contains("TOP_KNIT");
    }

    @Test
    void 매핑되지_않는_카테고리는_빈_값을_반환한다() {
        when(categoryRepository.findById(2L)).thenReturn(Optional.of(category));
        when(category.getNameEn()).thenReturn("SNEAKERS");

        assertThat(mapper.resolve(2L)).isEmpty();
    }

    @Test
    void categoryId가_null이면_조회하지_않고_빈_값을_반환한다() {
        assertThat(mapper.resolve(null)).isEmpty();
    }
}
