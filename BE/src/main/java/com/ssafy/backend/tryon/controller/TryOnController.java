package com.ssafy.backend.tryon.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.tryon.dto.response.TryOnResultResponse;
import com.ssafy.backend.tryon.service.TryOnResultService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 생성(POST) 엔드포인트는 없다 — AI 시착 합성 계약이 아직 없어 이 범위에서는
// 저장/조회/삭제만 다룬다 (.claude/requests/ai/001-tryon-result-contract.md 참고).
// 경로는 APIs.md의 `/users/{id}/tryons` 스펙을 그대로 따른다(userId/id 두 path variable을
// 구분해야 해서 바깥쪽을 {userId}로 표기 — 같은 문서의 /users/{userId}/wishes/{id}와 동일한 표기 관례).
@Tag(name = "AI 가상 시착", description = "시착 결과 조회/삭제 API")
@RestController
@RequestMapping("/api/users/{userId}/tryons")
@RequiredArgsConstructor
public class TryOnController {

    private final TryOnResultService tryOnResultService;

    @Operation(
            summary = "시착 결과 목록 조회",
            description = "본인의 시착 결과 목록을 최신순으로 조회한다. 각 항목의 이미지 URL은 짧은 만료시간의 presigned GET URL이다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 시착 결과를 조회하려 함")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<List<TryOnResultResponse>>> getResults(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(tryOnResultService.getResults(userId)));
    }

    @Operation(summary = "시착 결과 상세 조회", description = "본인의 시착 결과 하나를 조회한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인의 시착 결과가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "시착 결과 없음")
    })
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<TryOnResultResponse>> getResult(
            Authentication authentication, @PathVariable Long userId, @PathVariable Long id) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(tryOnResultService.getResult(userId, id)));
    }

    @Operation(summary = "시착 결과 삭제", description = "본인의 시착 결과를 S3와 DB에서 함께 삭제한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인의 시착 결과가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "시착 결과 없음")
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteResult(
            Authentication authentication, @PathVariable Long userId, @PathVariable Long id) {
        requireSelf(authentication, userId);
        tryOnResultService.deleteResult(userId, id);
        return ResponseEntity.noContent().build();
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.TRYON_RESULT_NOT_OWNER);
        }
    }
}