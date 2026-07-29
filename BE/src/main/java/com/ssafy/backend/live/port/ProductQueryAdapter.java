package com.ssafy.backend.live.port;

import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * {@link ProductQueryPort}의 실제 구현. 상품 도메인의 리포지토리에 위임한다.
 *
 * <p>계획(JY005) 초안에서는 상품 도메인이 없어 스텁으로 두려 했으나, 상품 등록·조회(-238 등)가
 * 이미 들어와 있어 처음부터 실제 조회로 붙인다. 상품 도메인 코드는 읽기만 하고 수정하지 않는다.
 */
@Component
@RequiredArgsConstructor
public class ProductQueryAdapter implements ProductQueryPort {

    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;

    @Override
    public Optional<ProductSummary> findById(Long productId) {
        return productRepository.findById(productId)
                .map(product -> new ProductSummary(
                        product.getId(), product.getSeller().getId(), product.getTitle()));
    }

    @Override
    public List<CategorySummary> findRootCategories(Collection<Long> productIds) {
        if (productIds.isEmpty()) {
            return List.of();
        }

        List<Long> categoryIds = productRepository.findAllById(productIds).stream()
                .map(Product::getCategoryId)
                .distinct()
                .toList();
        if (categoryIds.isEmpty()) {
            return List.of();
        }

        // 소분류는 부모(대분류)로 올린다. 최상위는 parentId 가 없으므로 자기 자신이 대분류다.
        List<Long> rootIds = categoryRepository.findAllById(categoryIds).stream()
                .map(category -> category.getParentId() == null ? category.getId() : category.getParentId())
                .distinct()
                .toList();

        return categoryRepository.findAllById(rootIds).stream()
                .sorted(Comparator.comparing(Category::getId))
                .map(category -> new CategorySummary(category.getId(), category.getName()))
                .toList();
    }
}