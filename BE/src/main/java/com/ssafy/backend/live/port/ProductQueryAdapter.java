package com.ssafy.backend.live.port;

import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
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
        return findRootCategoryByProductId(productIds).values().stream()
                .distinct()
                .sorted(Comparator.comparing(CategorySummary::id))
                .toList();
    }

    @Override
    public Map<Long, CategorySummary> findRootCategoryByProductId(Collection<Long> productIds) {
        if (productIds.isEmpty()) {
            return Map.of();
        }

        List<Product> products = productRepository.findAllById(productIds);
        if (products.isEmpty()) {
            return Map.of();
        }

        // 소분류는 부모(대분류)로 올린다. 최상위는 parentId 가 없으므로 자기 자신이 대분류다.
        Map<Long, Long> rootIdByCategoryId = categoryRepository
                .findAllById(products.stream().map(Product::getCategoryId).distinct().toList()).stream()
                .collect(Collectors.toMap(
                        Category::getId,
                        category -> category.getParentId() == null ? category.getId() : category.getParentId()));

        Map<Long, CategorySummary> rootById = categoryRepository
                .findAllById(Set.copyOf(rootIdByCategoryId.values())).stream()
                .collect(Collectors.toMap(
                        Category::getId, category -> new CategorySummary(category.getId(), category.getName())));

        return products.stream()
                .filter(product -> rootIdByCategoryId.containsKey(product.getCategoryId()))
                .collect(Collectors.toMap(
                        Product::getId,
                        product -> rootById.get(rootIdByCategoryId.get(product.getCategoryId())),
                        (a, b) -> a));
    }

    @Override
    public List<Long> findProductIdsInCategories(Collection<Long> categoryIds) {
        if (categoryIds.isEmpty()) {
            return List.of();
        }

        // 대분류를 고르면 하위 소분류 상품까지 잡아야 한다. 요청에 소분류가 섞여 있어도
        // 그 소분류는 자식이 없으므로 확장 결과가 자기 자신뿐이라 그대로 동작한다.
        Set<Long> expanded = new LinkedHashSet<>(categoryIds);
        categoryRepository.findByParentIdIn(categoryIds).forEach(child -> expanded.add(child.getId()));

        return productRepository.findByCategoryIdIn(expanded).stream()
                .map(Product::getId)
                .toList();
    }
}