package com.ssafy.backend.global.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public enum ErrorCode {

    // [공통]
    INVALID_INPUT_VALUE(HttpStatus.BAD_REQUEST, "C001", "잘못된 입력값입니다."),
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "C002", "서버 내부 오류가 발생했습니다."),
    METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED, "C003", "허용되지 않은 HTTP 메서드입니다."),

    // [인증/회원]
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "U001", "존재하지 않는 사용자입니다."),
    SSO_LOGIN_FAILED(HttpStatus.UNAUTHORIZED, "U002", "싸피어스 SSO 로그인에 실패했습니다."),
    DUPLICATE_EMAIL(HttpStatus.CONFLICT, "U003", "이미 가입된 이메일입니다."),
    ONBOARDING_REQUIRED(HttpStatus.FORBIDDEN, "U004", "온보딩을 완료해야 이용할 수 있습니다."),
    INVALID_VERIFICATION_CODE(HttpStatus.BAD_REQUEST, "U005", "인증 코드가 일치하지 않거나 만료되었습니다."),
    EMAIL_VERIFICATION_REQUIRED(HttpStatus.BAD_REQUEST, "U006", "이메일 인증이 필요합니다."),
    TOO_MANY_VERIFICATION_ATTEMPTS(HttpStatus.BAD_REQUEST, "U007", "인증 시도 횟수를 초과했습니다. 인증코드를 재발송해주세요."),
    TOO_MANY_VERIFICATION_REQUESTS(HttpStatus.TOO_MANY_REQUESTS, "U008", "인증코드 요청이 너무 많습니다. 잠시 후 다시 시도해주세요."),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "U009", "이메일 또는 비밀번호가 일치하지 않습니다."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "U010", "유효하지 않은 토큰입니다."),
    EXPIRED_TOKEN(HttpStatus.UNAUTHORIZED, "U011", "만료된 토큰입니다."),

    // [라이브/채팅]
    LIVE_NOT_FOUND(HttpStatus.NOT_FOUND, "L001", "진행 중이거나 예약된 라이브가 없습니다."),
    MESSAGE_BLOCKED(HttpStatus.FORBIDDEN, "L002", "숨김 또는 차단 처리된 메시지입니다."),
    STT_PROCESSING_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "L003", "STT 변환 처리에 실패했습니다."),
    NOT_LIVE_HOST(HttpStatus.FORBIDDEN, "L004", "본인이 개설한 라이브만 처리할 수 있습니다."),
    PRODUCT_ALREADY_LINKED(HttpStatus.CONFLICT, "L005", "이미 라이브에 연결된 상품입니다."),
    LIVE_PRODUCT_NOT_FOUND(HttpStatus.NOT_FOUND, "L006", "라이브에 연결되지 않은 상품입니다."),
    INVALID_LIVE_STATE(HttpStatus.BAD_REQUEST, "L007", "현재 방송 상태에서는 해당 처리를 할 수 없습니다."),

    // [경매/입찰]
    AUCTION_NOT_ACTIVE(HttpStatus.BAD_REQUEST, "A001", "현재 진행 중인 경매가 아닙니다."),
    BID_LOWER_THAN_CURRENT(HttpStatus.BAD_REQUEST, "A002", "입찰 금액이 현재 최고가보다 낮습니다."),
    AUCTION_ALREADY_CLOSED(HttpStatus.BAD_REQUEST, "A003", "이미 종료된 경매입니다."),
    AUCTION_ALREADY_CONFIGURED(HttpStatus.CONFLICT, "A004", "해당 상품에 이미 설정된 경매가 있습니다."),

    // [지갑/주문]
    INSUFFICIENT_POINTS(HttpStatus.BAD_REQUEST, "W001", "포인트 잔액이 부족합니다."),
    WITHDRAWAL_LIMIT_EXCEEDED(HttpStatus.BAD_REQUEST, "W002", "출금 가능 금액을 초과했습니다."),
    INVALID_ORDER_STATE(HttpStatus.BAD_REQUEST, "O001", "현재 상태에서는 해당 처리를 할 수 없습니다."),

    // [AI 가상 시착]
    TRYON_PROFILE_NOT_FOUND(HttpStatus.NOT_FOUND, "T001", "가상 시착 프로필이 등록되지 않았습니다."),
    TRYON_GENERATION_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "T002", "가상 시착 이미지 생성 중 오류가 발생했습니다."),
    TRYON_RESULT_NOT_FOUND(HttpStatus.NOT_FOUND, "T003", "존재하지 않는 시착 결과입니다."),
    TRYON_RESULT_NOT_OWNER(HttpStatus.FORBIDDEN, "T004", "본인의 시착 결과만 처리할 수 있습니다."),

    // [상품]
    PRODUCT_NOT_FOUND(HttpStatus.NOT_FOUND, "P001", "존재하지 않는 상품입니다."),
    NOT_PRODUCT_OWNER(HttpStatus.FORBIDDEN, "P002", "본인이 등록한 상품만 처리할 수 있습니다."),
    INVALID_PRODUCT_STATE(HttpStatus.BAD_REQUEST, "P003", "현재 상태에서는 해당 처리를 할 수 없습니다."),
    PRODUCT_IMAGE_NOT_FOUND(HttpStatus.NOT_FOUND, "P004", "존재하지 않는 상품 이미지입니다."),
    PRODUCT_IMAGE_LIMIT_EXCEEDED(HttpStatus.BAD_REQUEST, "P005", "상품 이미지는 최대 10장까지 등록할 수 있습니다."),
    INVALID_IMAGE_TYPE(HttpStatus.BAD_REQUEST, "P006", "지원하지 않는 이미지 형식입니다."),
    PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED(HttpStatus.BAD_REQUEST, "P007", "업로드가 확인되지 않았습니다. 먼저 파일을 업로드해주세요."),
    CATEGORY_NOT_FOUND(HttpStatus.BAD_REQUEST, "P008", "존재하지 않는 카테고리입니다."),

    // [소셜(팔로우/찜)]
    WISH_ALREADY_EXISTS(HttpStatus.CONFLICT, "S001", "이미 찜한 상품입니다."),
    WISH_NOT_FOUND(HttpStatus.NOT_FOUND, "S002", "찜하지 않은 상품입니다."),
    WISH_FORBIDDEN(HttpStatus.FORBIDDEN, "S003", "본인의 찜만 처리할 수 있습니다.");

    private final HttpStatus status;
    private final String code;
    private final String message;

    ErrorCode(HttpStatus status, String code, String message) {
        this.status = status;
        this.code = code;
        this.message = message;
    }
}