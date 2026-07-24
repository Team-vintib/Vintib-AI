package com.ssafy.backend.global.response;

import com.ssafy.backend.global.exception.ErrorCode;

public record ApiResponse<T>(boolean success, T data, ErrorResponse error) {

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, data, null);
    }

    public static ApiResponse<?> error(ErrorCode errorCode) {
        return new ApiResponse<>(false, null, ErrorResponse.of(errorCode));
    }

    public static ApiResponse<?> error(ErrorResponse errorResponse) {
        return new ApiResponse<>(false, null, errorResponse);
    }
}