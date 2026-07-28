package com.ssafy.backend.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.ssafy.backend.product.dto.response.CategoryResponse;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CategoryServiceTest {

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private Category outer;

    @Mock
    private Category jacket;

    private CategoryService categoryService;

    @BeforeEach
    void setUp() {
        categoryService = new CategoryService(categoryRepository);
    }

    @Test
    void 전체_카테고리_목록을_id_오름차순으로_반환한다() {
        when(outer.getId()).thenReturn(1L);
        when(outer.getParentId()).thenReturn(null);
        when(outer.getName()).thenReturn("아우터");
        when(outer.getDepth()).thenReturn((short) 1);
        when(jacket.getId()).thenReturn(2L);
        when(jacket.getParentId()).thenReturn(1L);
        when(jacket.getName()).thenReturn("자켓");
        when(jacket.getDepth()).thenReturn((short) 2);
        when(categoryRepository.findAllByOrderByIdAsc()).thenReturn(List.of(outer, jacket));

        List<CategoryResponse> responses = categoryService.getAllCategories();

        assertThat(responses).hasSize(2);
        assertThat(responses.get(0).id()).isEqualTo(1L);
        assertThat(responses.get(0).parentId()).isNull();
        assertThat(responses.get(1).parentId()).isEqualTo(1L);
        assertThat(responses.get(1).name()).isEqualTo("자켓");
    }
}
