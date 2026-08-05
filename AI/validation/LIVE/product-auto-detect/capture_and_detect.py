"""로컬 웹캠으로 "판매자가 상품을 카메라에 들어 보이는 순간"을 시뮬레이션해서
YOLO(감지) -> 분류(카테고리) 2단계 파이프라인이 개념적으로 성립하는지 검증하는 PoC.
설계: `.claude/plans/ai/CH018-live-product-detect-poc.md`.

**감지 방식(계획 대비 변경)**: 계획에는 "사람 근처에 크게 잡히는 미분류 전경 객체"를
후보로 잡는다고 적었는데, 실제로 짜보니 표준 YOLO(닫힌 클래스셋)는 COCO 80개 클래스
밖의 물체는 아예 박스 자체를 안 뱉는다 -- "미분류 박스"라는 게 없다. 그래서 물체
탐지 대신 **YOLO11-pose(사람 키포인트 탐지)로 손목 위치를 앵커로 쓴다**: 손목 위치가
N프레임 동안 안정적으로 멈춰 있으면, 손목 주변을 크롭한다. 클래스에 의존하지 않으니
옷이든 모자든 신발이든 종류 상관없이 같은 방식으로 잡을 수 있다.

**"팔을 뻗어야 트리거"는 1차 실사용 테스트 후 제거했다**: 처음엔 손목이 어깨에서 일정
거리 이상 떨어져야("팔을 뻗은 자세") 후보로 잡았는데, 실제 라이브에서는 판매자가 팔을
쭉 뻗기보다 몸/얼굴 가까이에서 상품을 보여주는 경우가 더 많을 거라는 피드백으로
제거했다. 지금은 손이 어디 있든(몸통 앞이든 얼굴 옆이든) **가만히 멈춰만 있으면**
트리거된다 -- 양쪽 손목을 각각 독립적으로 추적해서, 먼저 안정화되는 쪽을 쓴다.

**양손 사용 케이스 추가(2차 실사용 테스트 후)**: 시계처럼 양손으로 붙잡고 보여주는
물건은 실제 물건이 두 손목의 "중간"에 있는데, 손목 하나만 중심으로 크롭하니 물건이
아니라 얼굴/몸 쪽으로 크롭이 치우치는 문제가 실측으로 확인됐다. 양쪽 손목이 둘 다
보이면 **중점**을 별도 후보("both")로 추가 추적한다 -- 크롭 반경은 두 손목 사이 거리
기준으로 잡아서(안정성 판정용 허용 오차는 기존처럼 어깨너비 기준 유지, 크롭 크기만
손목 간 거리 기준으로 분리) 물건의 실제 폭에 맞춰 커지고 작아진다. "both"가 안정화되면
개별 손목보다 우선한다.

**스케일 기준(1차 테스트 후 변경)**: 어깨~엉덩이(torso) 길이를 기준으로 크롭 반경을
잡았더니, 사람이 카메라에 가까이 붙으면(특히 얼굴 가까이 물건을 들어 보일 때) 엉덩이가
프레임 밖으로 나가 torso 추정이 부정확해지고 크롭이 지나치게 좁게 잡히는 문제가 실측으로
확인됐다. 어깨너비(좌우 어깨 사이 거리)는 카메라에 가까이 붙어도 훨씬 안정적으로
보이므로 스케일 기준을 어깨너비로 바꿨다.

**설명 방식(계획 대비 변경)**: VLM으로 문장형 설명을 생성하는 대신, 이미 검증된 상품
분류기(`AI/validation/CLASS/product-info-check/classify.py`, `fashion_clip` zero-shot,
소분류 35종 top-1 0.79/top-3 1.00 실측)를 그대로 재사용해 카테고리만 분류한다 -- 문장
생성보다 빠르고(임베딩 유사도 계산 vs VLM 토큰 생성) 이미 검증된 정확도가 있다.
**단, 그 정확도는 깨끗한 카탈로그 사진 기준이다** -- 손에 들고 웹캠으로 찍은, 손가락에
가려지고 흔들린 사진은 그보다 떨어지는 게 자연스럽다. 대분류 6-way를 먼저 물어보고 그
안에서 소분류를 좁히는 `classify_two_stage`가 35-way를 한 번에 묻는 것보다 대분류를
아예 잘못 짚는 오답(예: 신발을 가방으로 착각)을 줄여줄 걸로 기대해 이걸로 바꿨다.

**중복 등록 방지**: 같은 물건을 계속 들고 있거나 잠시 후 다시 보여주면 같은 상품이 여러
번 등록되는 걸 막아야 한다. 분류기가 이미 CLIP류 이미지 임베딩을 계산하므로, 새로
캡처될 때마다 그 임베딩을 지금까지 등록된 물건들의 임베딩과 코사인 유사도로 비교해서
`DUPLICATE_SIMILARITY_THRESHOLD` 이상이면 중복으로 보고 건너뛴다. 임계값은 실측 없이
잡은 초기값이라(0.90) 실제 유사도 로그를 보면서 조정이 필요하다.

conda 환경: `live-product-detect`.
"""

import os
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

_PRODUCT_INFO_CHECK_DIR = os.path.abspath(
    os.path.join("..", "..", "CLASS", "product-info-check")
)
if _PRODUCT_INFO_CHECK_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_INFO_CHECK_DIR)

from classify import classify_two_stage, get_category_classifier  # noqa: E402
from taxonomy import _KR_LABELS  # noqa: E402

OUT_DIR = "result"
os.makedirs(OUT_DIR, exist_ok=True)

CAMERA_INDEX = 0
YOLO_MODEL = "yolo11n-pose.pt"
CATEGORY_BACKEND = "fashion_clip"
TEMPLATE_KEY = "en_clip_style"  # REPORT.md 벤치마크 기본값 -- "들어 보이는 사진" 스타일로
# 튜닝된 건 아니라 실측하면서 kr_plain/kr_secondhand_flat과 비교해볼 것.

PERSON_CONF_THRESHOLD = 0.5
KEYPOINT_CONF_THRESHOLD = 0.5
STABILITY_RADIUS_RATIO = 0.2  # 안정 판정 허용 반경(x 어깨너비)
STABLE_FRAMES_REQUIRED = 7
COOLDOWN_SEC = 5.0
CROP_RADIUS_RATIO = 1.3  # 크롭 반경(x 어깨너비)
MIN_CROP_RADIUS_PX = 120
DUPLICATE_SIMILARITY_THRESHOLD = 0.90  # 이 이상 유사하면 같은 물건으로 보고 건너뜀(초기값, 튜닝 필요)

# COCO keypoint 인덱스 (YOLO pose 기본 포맷)
L_SHOULDER, R_SHOULDER = 5, 6
L_WRIST, R_WRIST = 9, 10


def shoulder_width(kpts_xy: np.ndarray, kpts_conf: np.ndarray) -> float | None:
    if kpts_conf[L_SHOULDER] < KEYPOINT_CONF_THRESHOLD or kpts_conf[R_SHOULDER] < KEYPOINT_CONF_THRESHOLD:
        return None
    return float(np.linalg.norm(kpts_xy[L_SHOULDER] - kpts_xy[R_SHOULDER]))


def find_candidate_wrists(kpts_xy: np.ndarray, kpts_conf: np.ndarray) -> dict[str, np.ndarray]:
    """신뢰도가 충분한 손목 위치를 전부 반환한다(뻗은 정도는 안 본다). {"left": xy, "right": xy}."""
    candidates = {}
    if kpts_conf[L_WRIST] >= KEYPOINT_CONF_THRESHOLD:
        candidates["left"] = kpts_xy[L_WRIST].copy()
    if kpts_conf[R_WRIST] >= KEYPOINT_CONF_THRESHOLD:
        candidates["right"] = kpts_xy[R_WRIST].copy()
    return candidates


def embed_image(classifier, image_path: Path):
    """분류기가 이미 갖고 있는 `_embed()`(이미지+텍스트 인코딩)를 재사용해 이미지
    임베딩만 뽑는다. 텍스트는 API를 맞추기 위한 더미 1개만 넣고 버린다 -- 두 번째
    `_embed()` 호출(분류용)과 별개라 약간 비효율이지만, PoC 범위에서는 무시할 만하다."""
    image_embeds, _ = classifier._embed(image_path, ["product"])
    return image_embeds[0]  # (D,) L2-정규화됨


def crop_around(frame: np.ndarray, center: np.ndarray, radius_px: float) -> np.ndarray:
    h, w = frame.shape[:2]
    cx, cy = int(center[0]), int(center[1])
    r = int(radius_px)
    x0, x1 = max(0, cx - r), min(w, cx + r)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    return frame[y0:y1, x0:x1]


def main():
    print("=== YOLO11-pose 로드 ===")
    yolo = YOLO(YOLO_MODEL)

    print(f"=== 카테고리 분류기 로드 ({CATEGORY_BACKEND}) ===")
    t0 = time.time()
    classifier = get_category_classifier(CATEGORY_BACKEND)
    print(f"완료 ({time.time() - t0:.1f}s)")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"카메라 {CAMERA_INDEX}를 열 수 없습니다")

    position_history: dict[str, deque[np.ndarray]] = {
        "both": deque(maxlen=STABLE_FRAMES_REQUIRED),
        "left": deque(maxlen=STABLE_FRAMES_REQUIRED),
        "right": deque(maxlen=STABLE_FRAMES_REQUIRED),
    }
    last_trigger_time = 0.0
    shot_count = 0
    registered_count = 0
    registered_embeddings: list = []  # 등록된 물건들의 이미지 임베딩 (중복 판정용)
    registered_labels: list[str] = []

    print("\n=== 실행 중 (창에 포커스한 뒤 'q'로 종료) ===")
    print("상품을 손에 들고 카메라 앞에 가만히 보여주세요 (팔을 뻗지 않아도 됩니다).")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("프레임을 읽지 못했습니다")
                break

            results = yolo.predict(frame, conf=PERSON_CONF_THRESHOLD, verbose=False)[0]
            display = frame.copy()

            wrists: dict[str, np.ndarray] = {}
            scale = None
            if results.keypoints is not None and len(results.keypoints) > 0:
                kpts_xy_all = results.keypoints.xy.cpu().numpy()
                kpts_conf_all = results.keypoints.conf
                kpts_conf_all = kpts_conf_all.cpu().numpy() if kpts_conf_all is not None else None

                # 첫 번째로 잡힌 사람만 추적 (다중 인물은 범위 밖)
                kpts_xy = kpts_xy_all[0]
                kpts_conf = kpts_conf_all[0] if kpts_conf_all is not None else np.ones(len(kpts_xy))
                scale = shoulder_width(kpts_xy, kpts_conf)
                wrists = find_candidate_wrists(kpts_xy, kpts_conf)

            display = results.plot(img=display)

            now = time.time()
            in_cooldown = (now - last_trigger_time) < COOLDOWN_SEC

            # 후보 위치 조립: "both"(양손 중점, 물건이 실제로 있을 확률이 높음)를 있으면
            # 최우선으로 두고, 개별 손목은 폴백으로 남긴다. 안정성 판정 허용 오차는 전부
            # 어깨너비 기준(카메라와의 거리에 안정적)으로 통일하고, 크롭 반경만 "both"는
            # 손목 간 거리 기준으로 따로 잡는다(물건의 실제 폭을 반영).
            positions: dict[str, np.ndarray] = {}
            crop_scales: dict[str, float] = {}
            if scale is not None and scale > 1e-3:
                if "left" in wrists and "right" in wrists:
                    positions["both"] = (wrists["left"] + wrists["right"]) / 2.0
                    hand_distance = float(np.linalg.norm(wrists["left"] - wrists["right"]))
                    crop_scales["both"] = max(hand_distance / 2.0, scale / 2.0)
                for side in ("left", "right"):
                    if side in wrists:
                        positions[side] = wrists[side]
                        crop_scales[side] = scale

            triggered = False
            if not in_cooldown:
                for name in ("both", "left", "right"):
                    history = position_history[name]
                    if name not in positions:
                        history.clear()
                        continue

                    pos = positions[name]
                    history.append(pos)

                    stable = False
                    if len(history) == STABLE_FRAMES_REQUIRED:
                        pts = np.stack(history)
                        spread = float(np.linalg.norm(pts - pts.mean(axis=0), axis=1).max())
                        stable = spread < STABILITY_RADIUS_RATIO * scale

                    status = f"{name} stabilizing {len(history)}/{STABLE_FRAMES_REQUIRED}"
                    y_offset = {"both": 30, "left": 60, "right": 90}[name]
                    cv2.circle(display, (int(pos[0]), int(pos[1])), 8, (0, 255, 255), 2)
                    cv2.putText(display, status, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    if stable and not triggered:
                        radius_px = max(MIN_CROP_RADIUS_PX, CROP_RADIUS_RATIO * crop_scales[name])
                        crop = crop_around(frame, pos, radius_px)
                        if crop.size > 0:
                            shot_count += 1
                            timestamp = time.strftime("%Y%m%d_%H%M%S")
                            crop_path = os.path.join(OUT_DIR, f"crop_{timestamp}_{shot_count}.png")
                            frame_path = os.path.join(OUT_DIR, f"frame_{timestamp}_{shot_count}.png")
                            cv2.imwrite(crop_path, crop)
                            cv2.imwrite(frame_path, display)

                            print(f"\n=== 캡처 #{shot_count} -> {crop_path} (반경 {radius_px:.0f}px) ===")

                            embedding = embed_image(classifier, Path(crop_path))
                            best_sim, best_idx = -1.0, -1
                            for i, prev in enumerate(registered_embeddings):
                                sim = float((embedding @ prev).item())
                                if sim > best_sim:
                                    best_sim, best_idx = sim, i

                            if best_sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                                print(
                                    f"중복으로 판단(유사도 {best_sim:.3f} >= "
                                    f"{DUPLICATE_SIMILARITY_THRESHOLD}, 기존 #{best_idx + 1} "
                                    f"{registered_labels[best_idx]}) -- 건너뜁니다"
                                )
                            else:
                                if best_idx >= 0:
                                    print(f"(최고 유사도 {best_sim:.3f}, 기존 #{best_idx + 1} -- 중복 아님)")
                                print("분류 중...")
                                t0 = time.time()
                                result = classify_two_stage(classifier, Path(crop_path), TEMPLATE_KEY, top_k=3)
                                elapsed = time.time() - t0
                                label_kr = _KR_LABELS.get(result.predicted, result.predicted)
                                print(f"분류 결과({elapsed:.2f}s): {label_kr} ({result.predicted}, {result.score:.3f})")
                                top3 = ", ".join(
                                    f"{_KR_LABELS.get(c.code, c.code)} {c.score:.3f}" for c in result.candidates
                                )
                                print(f"  상위 후보: {top3}")

                                registered_embeddings.append(embedding)
                                registered_labels.append(label_kr)
                                registered_count += 1

                        last_trigger_time = now
                        triggered = True

                if triggered:
                    for history in position_history.values():
                        history.clear()
            else:
                for history in position_history.values():
                    history.clear()
                if in_cooldown:
                    remaining = COOLDOWN_SEC - (now - last_trigger_time)
                    cv2.putText(display, f"cooldown {remaining:.1f}s", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)

            cv2.imshow("product-auto-detect", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(
        f"\n=== 종료 (총 {shot_count}회 캡처, {registered_count}건 등록, "
        f"{shot_count - registered_count}건 중복 스킵, 결과는 {OUT_DIR}/ 참고) ==="
    )


if __name__ == "__main__":
    main()
