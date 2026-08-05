import type { Router } from 'vue-router'

// VinTib 스크롤 리빌 (스펙 §10)
// - 섹션 진입 시 자식들을 vtReveal(opacity/translateY/blur)로 55ms 스태거 리빌, 1회.
// - 콘텐츠를 미리 숨기지 않는다: 옵저버가 진입 시에만 애니메이션을 '추가'한다.
//   옵저버가 실패해도 화면은 그대로 보인다(안전장치로 1500ms 후 잔여 opacity 정리).
// - prefers-reduced-motion: reduce 에서는 아무것도 하지 않는다.

const STAGGER_MS = 55
const STAGGER_CAP = 8
const REVEAL = 'vtReveal 620ms cubic-bezier(0.22, 1, 0.36, 1) both'

let observer: IntersectionObserver | null = null
const observed = new WeakSet<Element>()

const revealTargets = () =>
  document.querySelectorAll<HTMLElement>('main section, main [data-reveal]')

const scan = () => {
  if (!observer) return

  requestAnimationFrame(() => {
    revealTargets().forEach((el) => {
      if (!observed.has(el) && el.children.length > 0) {
        observed.add(el)
        observer!.observe(el)
      }
    })
  })
}

const clearLeftover = () => {
  document.querySelectorAll<HTMLElement>('main *').forEach((el) => {
    if (el.style.opacity === '0') {
      el.style.opacity = ''
    }
  })
}

export function setupScrollReveal(router: Router) {
  if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
    return
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return
        }

        Array.from(entry.target.children).forEach((child, index) => {
          const el = child as HTMLElement
          el.style.animation = REVEAL
          el.style.animationDelay = `${Math.min(index, STAGGER_CAP) * STAGGER_MS}ms`
        })

        observer?.unobserve(entry.target)
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -6% 0px' },
  )

  scan()

  // 비동기로 렌더되는 섹션(데이터 로딩 후 등)을 잡기 위해 DOM 변화를 관찰한다.
  let scanScheduled = false
  const mutationObserver = new MutationObserver(() => {
    if (scanScheduled) {
      return
    }

    scanScheduled = true
    window.setTimeout(() => {
      scanScheduled = false
      scan()
    }, 120)
  })

  mutationObserver.observe(document.body, { childList: true, subtree: true })

  router.afterEach(() => {
    window.setTimeout(scan, 80)
    window.setTimeout(clearLeftover, 1500)
  })

  window.setTimeout(clearLeftover, 1500)
}
