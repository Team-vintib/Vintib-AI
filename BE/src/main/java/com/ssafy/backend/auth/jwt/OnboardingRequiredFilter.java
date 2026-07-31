package com.ssafy.backend.auth.jwt;

import tools.jackson.databind.ObjectMapper;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 온보딩 완료 강제 게이트 (SY019). {@link JwtAuthenticationFilter} 바로 뒤에서 실행되며,
 * 인증된 요청 중 화이트리스트를 제외한 나머지를 {@code onboardingCompleted == false}인
 * 회원에게 403 {@code ONBOARDING_REQUIRED}로 막는다.
 *
 * <p>인증되지 않은 요청(토큰 없음)은 이 필터에서 손대지 않는다 — 인증 자체가 필요한지는
 * {@code SecurityConfig}의 {@code authorizeHttpRequests}가 이미 판단한다. 다만 permitAll
 * 엔드포인트(비회원도 접근 가능)에 토큰을 실어 보내는 경우도 있어(예: 홈 개인화, 라이브 시청),
 * 그런 경로는 인증 여부와 무관하게 이 게이트에서도 예외로 둬야 한다 — 그래서 화이트리스트에
 * "온보딩 API 자체"뿐 아니라 "인증 없이도 원래 열려 있는 경로"까지 포함한다. 경로가 같아도
 * 메서드가 다르면(예: 상품 상세는 GET만 공개, 같은 경로의 PATCH/DELETE는 아님) 메서드까지
 * 맞춰서 화이트리스트를 좁힌다.
 */
@Component
@RequiredArgsConstructor
public class OnboardingRequiredFilter extends OncePerRequestFilter {

    /** {@code method}가 null이면 메서드 무관하게 매치한다. */
    private record WhitelistEntry(String method, String pattern) {
        boolean matches(String requestMethod, String path, AntPathMatcher matcher) {
            return (method == null || method.equalsIgnoreCase(requestMethod)) && matcher.match(pattern, path);
        }
    }

    /** 인증돼 있어도 온보딩 미완료 상태로 허용하는 경로 (SY019 "화이트리스트" 참고). */
    private static final List<WhitelistEntry> WHITELIST = List.of(
            // 토큰 재발급/로그아웃 — 온보딩 진행 중 액세스 토큰이 만료돼도 복구할 수 있어야 한다.
            new WhitelistEntry(null, "/api/auth/reissue"),
            new WhitelistEntry(null, "/api/auth/logout"),
            // 온보딩 API 자체(ONBOARD-001~004). /api/me/tryon(ONBOARD-003)은 아직 미구현이지만 미리 넣어둔다.
            new WhitelistEntry(null, "/api/users/*"),
            new WhitelistEntry(null, "/api/users/*/interests"),
            new WhitelistEntry(null, "/api/users/*/member-type"),
            new WhitelistEntry(null, "/api/me/tryon"),
            // SecurityConfig.PUBLIC_ENDPOINTS와 짝을 이루는 항목 — 비회원도 여는 경로라 토큰이
            // 실려 와도 온보딩 여부와 무관하게 통과해야 한다.
            new WhitelistEntry("GET", "/api/home"),
            new WhitelistEntry(null, "/api/health"),
            new WhitelistEntry(null, "/api/categories"),
            new WhitelistEntry(null, "/api/brands"),
            // 같은 경로라도 GET만 공개다 — PATCH/DELETE /api/products/{id}는 본인 확인이 필요해 제외.
            new WhitelistEntry("GET", "/api/products/*"),
            // 같은 경로라도 GET만 공개다 — POST /api/lives(즉시 개설)는 제외.
            new WhitelistEntry("GET", "/api/lives"),
            new WhitelistEntry("GET", "/api/lives/*"),
            new WhitelistEntry("GET", "/api/lives/*/chat-messages"),
            new WhitelistEntry("POST", "/api/lives/*/video-token")
    );

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    private final MemberRepository memberRepository;
    private final ObjectMapper objectMapper;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.isAuthenticated() && !isWhitelisted(request)) {
            Long memberId = (Long) authentication.getPrincipal();
            Member member = memberRepository.findById(memberId).orElse(null);
            if (member != null && !member.isOnboardingCompleted()) {
                writeErrorResponse(response, ErrorCode.ONBOARDING_REQUIRED);
                return;
            }
        }
        filterChain.doFilter(request, response);
    }

    private boolean isWhitelisted(HttpServletRequest request) {
        String path = request.getRequestURI();
        String method = request.getMethod();
        return WHITELIST.stream().anyMatch(entry -> entry.matches(method, path, PATH_MATCHER));
    }

    private void writeErrorResponse(HttpServletResponse response, ErrorCode errorCode) throws IOException {
        response.setStatus(errorCode.getStatus().value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        response.getWriter().write(objectMapper.writeValueAsString(ApiResponse.error(errorCode)));
    }
}
