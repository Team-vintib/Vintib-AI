package com.ssafy.backend.auth.jwt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.PrintWriter;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import tools.jackson.databind.ObjectMapper;

@ExtendWith(MockitoExtension.class)
class OnboardingRequiredFilterTest {

    private static final Long MEMBER_ID = 1L;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @Mock
    private Member member;

    @Mock
    private PrintWriter writer;

    private OnboardingRequiredFilter filterWithRepository() {
        return new OnboardingRequiredFilter(memberRepository, new ObjectMapper());
    }

    @AfterEach
    void clearContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void 인증되지_않은_요청은_그대로_통과한다() throws Exception {
        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        verify(response, never()).setStatus(org.mockito.ArgumentMatchers.anyInt());
    }

    @Test
    void 화이트리스트_경로는_온보딩_미완료여도_통과한다() throws Exception {
        인증_설정();
        when(request.getRequestURI()).thenReturn("/api/users/1/member-type");

        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        verify(memberRepository, never()).findById(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void 온보딩_미완료_회원이_화이트리스트_밖을_호출하면_403을_반환한다() throws Exception {
        인증_설정();
        when(request.getRequestURI()).thenReturn("/api/products");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(member.isOnboardingCompleted()).thenReturn(false);
        when(response.getWriter()).thenReturn(writer);

        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain, never()).doFilter(request, response);
        verify(response).setStatus(403);
    }

    @Test
    void GET_홈은_토큰이_있어도_온보딩_미완료면_통과한다() throws Exception {
        // /api/home은 permitAll이라 토큰이 실려 와도 온보딩 여부와 무관하게 열려 있어야 한다.
        인증_설정();
        when(request.getRequestURI()).thenReturn("/api/home");
        when(request.getMethod()).thenReturn("GET");

        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        verify(memberRepository, never()).findById(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void 같은_경로라도_POST_라이브_개설은_화이트리스트가_아니다() throws Exception {
        // GET /api/lives(목록 조회)는 공개지만 POST /api/lives(즉시 개설)는 아니다 — 경로가
        // 같아도 메서드로 구분돼야 한다.
        인증_설정();
        when(request.getRequestURI()).thenReturn("/api/lives");
        when(request.getMethod()).thenReturn("POST");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(member.isOnboardingCompleted()).thenReturn(false);
        when(response.getWriter()).thenReturn(writer);

        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain, never()).doFilter(request, response);
        verify(response).setStatus(403);
    }

    @Test
    void 온보딩을_완료한_회원은_화이트리스트_밖도_통과한다() throws Exception {
        인증_설정();
        when(request.getRequestURI()).thenReturn("/api/products");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(member.isOnboardingCompleted()).thenReturn(true);

        filterWithRepository().doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }

    private void 인증_설정() {
        var authentication = new UsernamePasswordAuthenticationToken(MEMBER_ID, null, List.of());
        SecurityContextHolder.getContext().setAuthentication(authentication);
    }
}
