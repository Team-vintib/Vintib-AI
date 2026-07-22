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

    // [라이브/채팅]
    LIVE_NOT_FOUND(HttpStatus.NOT_FOUND, "L001", "진행 중이거나 예약된 라이브가 없습니다."),
    MESSAGE_BLOCKED(HttpStatus.FORBIDDEN, "L002", "숨김 또는 차단 처리된 메시지입니다."),
    STT_PROCESSING_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "L003", "STT 변환 처리에 실패했습니다."),

    // [경매/입찰]
    AUCTION_NOT_ACTIVE(HttpStatus.BAD_REQUEST, "A001", "현재 진행 중인 경매가 아닙니다."),
    BID_LOWER_THAN_CURRENT(HttpStatus.BAD_REQUEST, "A002", "입찰 금액이 현재 최고가보다 낮습니다."),
    AUCTION_ALREADY_CLOSED(HttpStatus.BAD_REQUEST, "A003", "이미 종료된 경매입니다."),

    // [지갑/주문]
    INSUFFICIENT_POINTS(HttpStatus.BAD_REQUEST, "W001", "포인트 잔액이 부족합니다."),
    WITHDRAWAL_LIMIT_EXCEEDED(HttpStatus.BAD_REQUEST, "W002", "출금 가능 금액을 초과했습니다."),
    INVALID_ORDER_STATE(HttpStatus.BAD_REQUEST, "O001", "현재 상태에서는 해당 처리를 할 수 없습니다."),

    // [AI 가상 시착]
    TRYON_PROFILE_NOT_FOUND(HttpStatus.NOT_FOUND, "T001", "가상 시착 프로필이 등록되지 않았습니다."),
    TRYON_GENERATION_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "T002", "가상 시착 이미지 생성 중 오류가 발생했습니다.");

    private final HttpStatus status;
    private final String code;
    private final String message;

    ErrorCode(HttpStatus status, String code, String message) {
        this.status = status;
        this.code = code;
        this.message = message;
    }
}