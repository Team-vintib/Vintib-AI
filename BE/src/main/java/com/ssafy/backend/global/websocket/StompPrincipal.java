package com.ssafy.backend.global.websocket;

import java.security.Principal;

/**
 * STOMP 세션의 인증 주체. {@code memberId}를 들고 있다.
 *
 * <p>HTTP 쪽은 {@code UsernamePasswordAuthenticationToken}의 principal에 {@code memberId}(Long)를
 * 담고 컨트롤러가 그것을 캐스팅해 쓴다. STOMP는 {@link Principal}만 받으므로 같은 값을 담을
 * 최소 구현이 필요하다.
 *
 * <p><b>비회원은 이 객체를 갖지 않는다.</b> 즉 {@code principal == null}이 곧 "비회원"이다 —
 * 라이브 시청과 채팅 읽기는 비회원도 가능해야 하므로 연결 자체는 익명으로 통과시키고,
 * 발언·반응처럼 회원만 가능한 동작에서 principal 유무로 막는다.
 */
public record StompPrincipal(Long memberId) implements Principal {

    @Override
    public String getName() {
        return String.valueOf(memberId);
    }
}