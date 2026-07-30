package com.ssafy.backend.global.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.function.Function;

/**
 * 커서 페이징 응답. 오프셋 기반 {@link PageResponse}와 용도가 다르다.
 *
 * <p><b>계속 쌓이는 목록에는 오프셋을 쓸 수 없다.</b> 채팅·입찰처럼 조회하는 동안에도 새 행이
 * 들어오는 데이터는 {@code page=1}을 요청하는 순간 경계가 밀려 같은 항목이 두 번 보이거나
 * 빠진다. 커서는 "내가 마지막으로 본 ID"를 기준으로 잡아 그 문제가 생기지 않는다.
 *
 * <p>{@code totalElements}를 주지 않는 것도 의도다 — 매 요청마다 값이 바뀌는 전체 개수를
 * 세느라 COUNT 쿼리를 한 번 더 쏠 이유가 없다.
 */
public record CursorPageResponse<T>(

        List<T> content,

        @Schema(
                description = "다음 페이지 요청에 그대로 넣을 커서. 더 없으면 null",
                example = "1043")
        Long nextCursor,

        @Schema(description = "다음 페이지가 더 있는지", example = "true")
        boolean hasNext) {

    /**
     * 조회 결과에서 응답을 만든다. {@code items}에는 <b>요청 size보다 1건 더</b> 조회한 결과를
     * 넘긴다 — 초과분이 있으면 다음 페이지가 있다는 뜻이므로 COUNT 쿼리 없이 판정된다.
     */
    public static <E, T> CursorPageResponse<T> of(
            List<E> items, int size, Function<E, T> mapper, Function<E, Long> cursorExtractor) {
        boolean hasNext = items.size() > size;
        List<E> page = hasNext ? items.subList(0, size) : items;
        Long nextCursor = hasNext ? cursorExtractor.apply(page.get(page.size() - 1)) : null;

        return new CursorPageResponse<>(page.stream().map(mapper).toList(), nextCursor, hasNext);
    }
}