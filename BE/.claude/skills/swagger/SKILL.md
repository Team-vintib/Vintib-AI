---
name: swagger
description: Add/maintain Swagger(OpenAPI) docs for BE endpoints via springdoc-openapi — dependency setup, annotation conventions (@Tag/@Operation/@ApiResponses/@Schema), and a coverage audit. Use when scaffolding a new controller, adding endpoints, or when asked to check whether Swagger docs are complete.
---

# BE Swagger (OpenAPI)

## 0. 의존성 확인 (최초 1회)

`build.gradle`에 springdoc-openapi가 이미 있는지 먼저 확인한다. 없다면 추가한다.

```gradle
implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:<version>'
```

- 버전은 하드코딩하지 않는다 — Spring Boot 4.1.0(Spring Framework 7) 기준 최신 호환 버전을 그때 확인해서 넣고, 사용자에게 새 의존성 추가를 먼저 알린다.
- Spring Security 설정(`SecurityConfig` 등)이 생기면 아래 경로를 `permitAll`로 열어야 swagger-ui가 뜬다. 현재는 Security 설정 파일이 아직 없으니, 만들 때 함께 반영한다.
  - `/swagger-ui/**`
  - `/v3/api-docs/**`
- 로컬 확인: `http://localhost:8080/swagger-ui/index.html` (스펙 JSON: `/v3/api-docs`)

## 어노테이션 컨벤션

- 컨트롤러 클래스: `@Tag(name = "<도메인명>", description = "...")`
- 각 엔드포인트 메서드: `@Operation(summary = "...", description = "...")`
- 각 엔드포인트: `@ApiResponses`로 성공/실패 상태 코드 명시 (예외 처리 컨벤션이 생기면 그 에러코드와 맞춘다)
- 요청/응답 DTO(record) 필드: `@Schema(example = "...")`로 예시 값 표기

```java
@Tag(name = "경매", description = "실시간 경매 API")
@RestController
@RequestMapping("/api/auctions")
@RequiredArgsConstructor
public class AuctionController {

    private final AuctionService auctionService;

    @Operation(summary = "입찰", description = "포인트를 홀드하고 입찰을 등록한다.")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "입찰 성공"),
        @ApiResponse(responseCode = "400", description = "입찰 금액이 최소 증액 단위 미만")
    })
    @PostMapping("/{auctionId}/bids")
    public ResponseEntity<BidResponseDto> bid(
            @PathVariable Long auctionId,
            @Valid @RequestBody BidRequestDto request) {
        return ResponseEntity.ok(auctionService.bid(auctionId, request));
    }
}
```

```java
public record BidRequestDto(
        @Schema(example = "50000") @NotNull @Positive Long amount
) {
}
```

값(`example`, `summary`, 상태 코드 등)은 API 명세서에 적힌 그대로 옮긴다 — 명세서에 없는 내용을 지어내지 않는다.

## 커버리지 점검 (감사)

새 컨트롤러를 추가했거나 "스웨거 문서 다 되어있는지 확인해줘" 같은 요청을 받으면 아래를 grep으로 훑어 빠진 곳을 목록으로 보고한다.

```
# @Tag 없는 컨트롤러
grep -rL "@Tag" --include="*Controller.java" src/main/java

# 매핑 애너테이션 수 대비 @Operation 수가 적은 파일 확인 (파일별로)
grep -c "@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping" <file>
grep -c "@Operation" <file>

# @ApiResponses 없는 매핑 확인은 파일을 열어 메서드별로 직접 대조한다 (grep -c 만으로는 매핑-대응 여부까지는 못 봄)

# @Schema 없는 DTO record
grep -rL "@Schema" --include="*Dto.java" src/main/java/**/dto
```

빠진 항목은 임의로 채우지 않고, API 명세서를 참고해 사용자와 확인한 뒤 채운다.