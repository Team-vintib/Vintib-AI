// AI 품질 검증 결과의 bbox는 정규화 좌표 [x1, y1, x2, y2](0~1)로 온다
// (docs/requests/FE/036-quality-finding-bbox-rendering.md). 사진 위 오버레이는 기존
// {x,y,width,height}% 방식으로 그리므로, 렌더링 직전에만 이 형태로 변환한다.
export interface PercentBox {
  x: number
  y: number
  width: number
  height: number
}

export const toPercentBox = ([x1, y1, x2, y2]: [number, number, number, number]): PercentBox => ({
  x: x1 * 100,
  y: y1 * 100,
  width: (x2 - x1) * 100,
  height: (y2 - y1) * 100,
})
