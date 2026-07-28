package com.ssafy.backend.product.service;

import com.ssafy.backend.product.dto.response.CategoryResponse;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class CategoryService {

    private final CategoryRepository categoryRepository;

    public List<CategoryResponse> getAllCategories() {
        return categoryRepository.findAllByOrderByIdAsc().stream()
                .map(CategoryResponse::from)
                .toList();
    }
}
