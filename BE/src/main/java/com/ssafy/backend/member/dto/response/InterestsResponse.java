package com.ssafy.backend.member.dto.response;

import com.ssafy.backend.product.dto.response.BrandResponse;
import com.ssafy.backend.product.dto.response.CategoryResponse;
import java.util.List;

public record InterestsResponse(
        List<BrandResponse> brands,
        List<CategoryResponse> categories
) {
}
