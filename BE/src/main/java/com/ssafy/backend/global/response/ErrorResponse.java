package com.ssafy.backend.global.response;

import com.ssafy.backend.global.exception.ErrorCode;
import jakarta.validation.ConstraintViolation;
import java.util.List;

public record ErrorResponse(String code, String message, List<FieldError> errors) {

    public static ErrorResponse of(ErrorCode errorCode) {
        return new ErrorResponse(errorCode.getCode(), errorCode.getMessage(), null);
    }

    public static ErrorResponse of(ErrorCode errorCode, List<FieldError> errors) {
        return new ErrorResponse(errorCode.getCode(), errorCode.getMessage(), errors);
    }

    public record FieldError(String field, String value, String reason) {

        public static FieldError of(org.springframework.validation.FieldError fieldError) {
            Object rejectedValue = fieldError.getRejectedValue();
            return new FieldError(
                    fieldError.getField(),
                    rejectedValue == null ? "" : rejectedValue.toString(),
                    fieldError.getDefaultMessage()
            );
        }

        public static FieldError of(ConstraintViolation<?> violation) {
            Object invalidValue = violation.getInvalidValue();
            return new FieldError(
                    violation.getPropertyPath().toString(),
                    invalidValue == null ? "" : invalidValue.toString(),
                    violation.getMessage()
            );
        }
    }
}