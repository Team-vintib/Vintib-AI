"""로컬 웹캠으로 "판매자가 상품을 카메라에 보여주는 순간"을 시뮬레이션해서
감지 -> 분류(카테고리) 2단계 파이프라인이 개념적으로 성립하는지 검증하는 PoC.
설계: `.claude/plans/ai/CH018-live-product-detect-poc.md`.

**감지 방식(3차 개정)**: 1차는 "사람 근처에 크게 잡히는 미분류 전경 객체"였는데, 표준
YOLO(닫힌 클래스셋)는 COCO 80개 클래스 밖의 물체엔 박스 자체를 안 뱉어서 무산됐다.
2차는 YOLO11-pose로 손목 위치를 앵커 삼아 "손목이 멈춰 있으면 그 주변을 크롭"하는
방식이었는데, 실사용 테스트에서 "꼭 손으로 들어야 하나, 그냥 카메라에 물건만 들이대는
경우도 있지 않나"는 지적이 나왔다 -- 맞는 말이라, **포즈/손 추적을 아예 버리고 순수
프레임 차분(motion diff)으로 "화면에 새로 나타나서 잠시 멈춘 영역"을 직접 찾는 방식**으로
바꿨다. 손에 들었든 안 들었든, 카메라 앞에 갖다 대고 잠깐 멈추기만 하면 잡힌다.

**얼굴 제외 방식(4차 개정)**: "사람 bbox 위쪽 45%"라는 대략적인 추정으로는 부정확했다 --
실사용 테스트에서 물건(시계)을 얼굴 가까이 들고 있다가 **내리는 순간, 이번엔 얼굴 자체가
"막 멈춘 것"이 되어 얼굴만 캡처되는 문제**가 실측으로 확인됐다(팔/손이 움직이는 동안
얼굴도 미세하게 흔들리다가, 손을 내리고 나면 얼굴만 정지 상태로 남기 때문). 사람 bbox
비율 추정 대신 **OpenCV Haar cascade로 실제 얼굴 위치를 직접 검출**해서 그 주변만
정확히 제외하는 방식으로 바꿨다. 이 용도엔 YOLO가 더 이상 필요 없어서 뺐다(더
가볍고 빠름).

**5차 개정(실사용 재검증 후)**: Haar cascade 적용 뒤에도 두 가지가 또 실측으로 드러났다.
(1) 물건으로 눈/코를 가리면 그 프레임엔 얼굴 검출 자체가 실패해서 제외가 통째로 꺼지고,
얼굴+머리카락+손이 하나의 덩어리로 뭉쳐 잡혔다 -- 검출 실패 시 최근 `FACE_STALE_FRAMES`
프레임 이내의 마지막 얼굴 위치를 잠깐 재사용하도록 고쳤다. (2) 패딩 0.7은 웹캠에 얼굴을
가까이 댈 때(흔한 자세) 가슴 높이까지 제외 영역이 되어 정작 앞에 든 물건까지 같이
지워버렸다 -- 0.25로 줄였다. 이 둘이 겹치면 결과적으로 캡처된 bbox가 몸통 전체를
삼키거나 반대로 물건이 잘려나간 조각만 남았는데, 매번 다른 형태라 분류도 부정확하고
중복 판단(임베딩 유사도)도 안 맞았다 -- `MAX_STILL_AREA_FRAC` 상한을 추가해서, 후보
영역이 비정상적으로 크면(=몸통까지 뭉친 것) 그 프레임은 그냥 넘기도록 했다.

**6차 개정(모션 감지 정규화)**: 5차 개정 이후에도 여전히 천장+얼굴이 통째로 캡처되는
사례가 있어서 실제 캡처 프레임을 열어보니, 이번엔 흩뿌려진 노이즈가 아니라 **천장 전체가
하나의 거대한 덩어리로 "막 멈춘" 상태**였다 -- 카메라 자동노출/화이트밸런스가 조정되며
화면 전체 밝기가 한꺼번에 바뀌었다가 멈추는 걸 "전체가 움직였다 -> 방금 멈췄다"로 오인한
것으로 보인다(이웃 기반 노이즈 제거는 애초에 노이즈가 아니라 진짜 뭉친 덩어리라 효과가
없었다). `grid_motion_mask`에서 비교 전 각 프레임 평균 밝기를 빼도록(정규화) 고쳤다 --
균일한 밝기 변화는 상쇄되고 국소적 변화(물건이 실제로 놓이는 것)만 남는다. 합성 테스트로
확인: 균일 밝기 변화(+25) 시 감지 셀 0개, 국소 변화(6x8 블록) 시 정확히 그 블록만 감지됨.

또한 이 세션에서 "표준 YOLO로 시계를 분류할 수 있지 않냐"는 두 가지 대안도 실측으로
검증했다 -- (a) COCO 탐지(`yolo11n.pt`)는 시계가 뚜렷한 프레임에서도 person만 잡고 watch는
아예 안 잡힘(COCO에 클래스가 없음), (b) 전체 프레임을 ImageNet 분류(`yolo11n-cls.pt`)에
그대로 주면 화면을 지배하는 사람/배경에 묻혀 완전히 엉뚱한 라벨이 나옴(예: lab_coat,
refrigerator). 둘 다 기각 -- 크롭으로 후보 영역을 좁힌 뒤 분류하는 지금 2단계 구조 자체는
유지해야 한다는 근거가 됐다.

**7차 개정(분류 백엔드를 CLIP -> VLM으로 교체)**: 크롭 자체를 고쳤는데도(6차 개정)
`fashion_clip`(패션 상품 80만 건으로 파인튜닝된 CLIP조차도)이 깨끗한 시계 크롭에서
SUNGLASSES를 97.7% 확신으로 확신했다 -- CLIP/SigLIP 계열 공통의 구조적 한계로 보인다
(`CLASS/product-info-check/REPORT.md` §14: 같은 taxonomy로 대분류 6-way를 직접 물으면
CLIP 0.20 vs VLM(Qwen3-VL) 1.00, N=10). 실측(`vlm_control.query_category()`)으로 확인:
시계 크롭 2/2 정확(WATCH), 워터마크 없는 배경 크롭엔 ACCESSORY로 헛짚지 않고 다른
카테고리를 답함. **분류(카테고리 판정)는 VLM으로 교체**하고, 중복 감지(임베딩 코사인
유사도)만 CLIP(`fashion_clip._embed()`, 가볍고 빠름)에 남겼다 -- VLM은 텍스트 생성
전용이라 임베딩 유사도 비교에는 애초에 안 맞는다.

conda 환경: `live-product-detect`. `opencv-python`은 5.0부터 `cv2.CascadeClassifier`
바인딩 자체가 빠졌으므로(대체 API인 `FaceDetectorYN`은 별도 ONNX 모델이 필요) `<5`로
고정해야 한다.

**8차 개정(VLM 분류 이후 실사용 재검증)**: 분류 자체는(7차) 잘 맞았지만 세 가지가 더
드러났다. (1) 캡처된 것 중 상당수가 시계가 아니라 **판매자 본인이 입고 있는 상의/자켓**이었다
(`crop_20260805_133000_3.png`는 손목+상의 소매뿐, 시계 없음) -- 얼굴 제외만으로는 몸통(어깨
아래로 계속 이어지는 옷)이 "막 멈춘 영역"으로 잡히는 걸 못 막는다. **YOLO11-pose로 어깨
키포인트를 찾아 그 아래(프레임 하단까지)를 제외 영역에 추가**했다 -- 손목 위치를 트리거
조건으로 쓰던 2차 개정과는 다르다(그때는 "손목이 있어야만 감지"라 기각됐다), 이번엔 순수
제외 마스크 계산용이라 감지 자체는 여전히 모션만으로 트리거된다. (2) `STABLE_FRAMES_REQUIRED`
(10프레임)가 실제로는 카메라 프레임레이트에 따라 0.3~0.5초 정도밖에 안 됐다 -- 너무 빨리
캡처된다는 지적에 맞춰 **프레임 수 대신 실제 경과 시간(초)으로 정지 판정**을 바꿨다(카메라
FPS가 기기마다 다르므로 프레임 수 기준은 애초에 부정확했다). (3) 중복 감지 임계값(0.90)이
분류 정확도 개선 전 기준으로 잡혀 있었는데, 실측해보니 **같은 물건이어도 크롭마다 프레임이
달라져 임베딩 유사도가 0.56~0.84 사이로 넓게 흩어졌다** -- 이제 VLM이 카테고리를 신뢰성
있게 맞히므로, **같은 카테고리로 분류된 것끼리만** 임베딩을 비교하고 임계값을 낮췄다(다른
카테고리는 애초에 비교 대상에서 뺀다 -- 카테고리가 다른데 우연히 임베딩이 비슷해서 오탐
중복 처리되는 걸 막는다).
"""

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 모델은 이미 로컬 캐시에 있음 -- 매 실행마다
# HF Hub에 신선도 확인하러 나가는 왕복(비인증 요청 경고 + 렉의 원인)을 생략한다.

import cv2
import numpy as np
from ultralytics import YOLO

_PRODUCT_INFO_CHECK_DIR = os.path.abspath(os.path.join("..", "..", "CLASS", "product-info-check"))
if _PRODUCT_INFO_CHECK_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_INFO_CHECK_DIR)

from classify import get_category_classifier  # noqa: E402
from taxonomy import _KR_LABELS  # noqa: E402
from vlm_control import query_category  # noqa: E402

OUT_DIR = "result"
os.makedirs(OUT_DIR, exist_ok=True)

CAMERA_INDEX = 0
CATEGORY_BACKEND = "fashion_clip"  # 분류가 아니라 중복 감지(임베딩 유사도)에만 쓴다 -- 아래
# "분류(카테고리) 판정" 참고.

FACE_MIN_SIZE_PX = 60  # 이보다 작은 얼굴 후보는 노이즈로 무시
FACE_EXCLUDE_PADDING_FRAC = 0.25  # 검출된 얼굴 bbox 사방으로 이 비율만큼 여유를 더해 제외
# (원래 0.7이었는데 실측해보니 웹캠에 얼굴을 가까이 대면 가슴 높이까지 제외 영역이 돼서
# 정작 그 앞에 든 물건까지 같이 지워버리는 문제가 있었다 -- 얼굴 바로 옆만 여유있게 잡는
# 정도로 줄였다)
FACE_STALE_SECONDS = 0.5  # 이 초 이내면 마지막으로 검출된 얼굴 위치를 계속 재사용한다.
# (물건으로 눈/코를 가리면 Haar cascade가 그 프레임엔 얼굴을 아예 못 찾는데, 그때 제외를
# 통째로 꺼버리면 얼굴+물건이 하나의 덩어리로 뭉쳐 잡히는 문제가 실측으로 확인됐다 -- 바로
# 직전까지 있던 얼굴 위치를 잠깐 우려먹는 게 "얼굴이 그 자리에서 안 움직였다"는 가정상 더 안전)

POSE_MODEL = "yolo11n-pose.pt"
POSE_CONF_THRESHOLD = 0.5
TORSO_EXCLUDE_PADDING_FRAC = 0.2  # 어깨 폭 좌우로 이 비율만큼 여유를 더해 제외

DUPLICATE_SIMILARITY_THRESHOLD = 0.60  # 이 이상 유사하면 같은 물건으로 보고 건너뜀.
# (원래 0.90 -- VLM으로 분류를 교체하기 전, 크롭 품질이 나쁠 때 기준. 실측해보니 같은
# 물건이어도 캡처마다 프레임/각도가 달라져 임베딩 유사도가 0.56~0.84로 넓게 흩어졌다.
# 이제 "같은 카테고리로 분류된 것끼리만" 비교하므로(아래 main() 참고) 임계값을 낮춰도
# 다른 카테고리와 오탐될 위험이 없다.)
COOLDOWN_SEC = 5.0

# --- 모션 정지 감지 파라미터 ---
# **"계속 멈춰 있던 것"과 "막 움직이다 방금 멈춘 것"은 다르다** -- 배경(벽 등)은 항상
# "최근 N초 동안 정지" 조건을 만족해버려서, 그 조건만으로는 배경과 새로 놓인 물건이
# 하나의 연결 영역으로 뭉쳐버린다(실측으로 발견). 그래서 블록별로 "마지막 움직임 이후
# 경과 시간(초)"을 추적해서, 그 값이 STABLE_SECONDS_REQUIRED~STABLE_SECONDS_MAX_AGE
# 구간(막 멈춘 직후)에 있는 블록만 후보로 잡는다 -- 오래 전부터 안 움직인 배경은 이
# 구간을 벗어나 자동으로 제외된다. (원래 프레임 수 기준이었는데, 카메라 FPS가 기기마다
# 달라 "10프레임"이 실제로는 0.3~0.5초밖에 안 되는 등 부정확했다 -- 실제 경과 시간으로
# 바꿔서 "2~3초 보여주면 캡처"를 기기와 무관하게 정확히 구현한다.)
GRID_COLS, GRID_ROWS = 40, 30  # 프레임을 이 크기로 축소해 블록 단위로 모션을 본다(속도용)
MOTION_DIFF_THRESHOLD = 16.0  # 그레이스케일 평균 밝기 차이(0~255) -- 이보다 크면 "움직임"
# (원래 10.0이었는데 실측 환경(조명 플리커가 있는 실내)에서 배경 전체가 노이즈성
# "움직임"으로 계속 잡혀 16.0으로 올렸다. 침식(위 largest_candidate_region)과 같이
# 노이즈 완화를 이중으로 건다.)
STABLE_SECONDS_REQUIRED = 2.5  # 움직임이 멈춘 뒤 이만큼 시간이 지나야 후보로 잡는다(2~3초 요구사항)
STABLE_SECONDS_MAX_AGE = 8.0  # 이보다 오래 정지해 있으면 배경으로 보고 제외
STARTUP_GRACE_SECONDS = 2.0  # 스크립트 시작 직후 배경 전체가 "막 멈춘 것"처럼 오탐되는 걸 방지
NEIGHBOR_VOTE_MIN = 3  # 3x3 이웃(자기 포함 9칸) 중 이 칸 수 이상 후보여야 살아남는다(노이즈 제거)
MIN_STILL_AREA_FRAC = 0.02  # 프레임 면적 대비 최소 크기(노이즈/작은 블롭 무시)
MAX_STILL_AREA_FRAC = 0.35  # 이보다 크면 물건 하나가 아니라 몸통/배경까지 뭉친 것으로 보고
# 버린다 -- 실측에서 얼굴 제외가 실패하면 얼굴+머리카락+손이 전부 하나의 연결 성분으로
# 뭉쳐서 잡혔는데, 그 bbox가 항상 프레임의 상당 부분(35% 이상)을 차지했다. 진짜 손에 든
# 물건은 팔을 벌려도 이 정도로 크게 뭉치지 않는다.
CROP_PADDING_FRAC = 0.15  # 찾은 정지 영역 bbox에 이 비율만큼 여백을 더해 크롭


_FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def detect_face_bbox(gray_frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """가장 큰 얼굴의 (x0,y0,x1,y1, 픽셀 좌표) 또는 None. 여러 얼굴이 잡히면(다른 사람이
    배경에 지나가는 등) 가장 큰 것만 -- 카메라에 가장 가까운 사람이 판매자일 확률이 높다."""
    faces = _FACE_CASCADE.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(FACE_MIN_SIZE_PX, FACE_MIN_SIZE_PX)
    )
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    pad_x, pad_y = int(fw * FACE_EXCLUDE_PADDING_FRAC), int(fh * FACE_EXCLUDE_PADDING_FRAC)
    return x - pad_x, y - pad_y, x + fw + pad_x, y + fh + pad_y


def detect_torso_bbox(pose_model: YOLO, frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """어깨 키포인트(COCO 5=왼쪽, 6=오른쪽) x범위를 프레임 하단까지 내린 (x0,y0,x1,y1)
    픽셀 bbox -- "판매자 본인이 입고 있는 옷"이 자리한 몸통 영역을 제외하기 위한
    용도로만 쓴다(트리거 조건이 아니다 -- 감지 자체는 여전히 순수 모션으로 트리거된다).

    엉덩이(11/12)까지 안 쓰는 이유: 웹캠 셀카 구도에서는 대개 엉덩이가 프레임 밖이라
    거의 항상 검출 실패한다. 어깨는 상반신 웹캠 샷에서 훨씬 안정적으로 잡히고, 몸통은
    물리적으로 어깨 아래로 계속 이어지므로 "어깨 x범위 x 프레임 하단까지"만으로도 충분한
    근사가 된다."""
    h, w = frame.shape[:2]
    results = pose_model(frame, verbose=False)
    if not results or results[0].keypoints is None or results[0].keypoints.xy.shape[0] == 0:
        return None
    r = results[0]

    # 여러 사람이 잡히면 박스 면적이 가장 큰(카메라에 가장 가까운) 사람만 -- 판매자일
    # 확률이 가장 높다.
    if r.boxes is not None and len(r.boxes) > 0:
        xyxy = r.boxes.xyxy.cpu().numpy()
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        idx = int(areas.argmax())
    else:
        idx = 0

    xy = r.keypoints.xy[idx].cpu().numpy()
    conf = r.keypoints.conf[idx].cpu().numpy() if r.keypoints.conf is not None else np.ones(len(xy))
    L_SHOULDER, R_SHOULDER = 5, 6
    shoulder_pts = [xy[i] for i in (L_SHOULDER, R_SHOULDER) if conf[i] >= POSE_CONF_THRESHOLD]
    if len(shoulder_pts) == 0:
        return None

    y_top = min(p[1] for p in shoulder_pts)
    if len(shoulder_pts) == 2:
        x0, x1 = sorted(p[0] for p in shoulder_pts)
    else:
        # 어깨 하나만 잡히면 폭을 알 수 없다 -- 프레임 폭의 일정 비율로 근사한다.
        cx = shoulder_pts[0][0]
        half = w * 0.15
        x0, x1 = cx - half, cx + half

    pad = (x1 - x0) * TORSO_EXCLUDE_PADDING_FRAC
    return int(max(0, x0 - pad)), int(max(0, y_top)), int(min(w, x1 + pad)), h


def grid_motion_mask(prev_gray_small: np.ndarray, gray_small: np.ndarray) -> np.ndarray:
    """두 축소 그레이스케일 프레임 사이 블록별 절대 밝기차 -- MOTION_DIFF_THRESHOLD보다
    크면 그 블록은 "이번 프레임에서 움직임"으로 본다.

    비교 전에 각 프레임에서 자기 평균 밝기를 뺀다(정규화) -- 카메라 자동노출/화이트밸런스가
    조정되면서 화면 전체 밝기가 한꺼번에 바뀌는 경우(실측으로 확인: 천장 전체가 하나의
    거대한 "막 멈춘" 덩어리로 잡혀 얼굴/배경이 캡처되는 원인이었다), 정규화 없이는 프레임
    전체가 "움직임"으로 잡힌다. 평균을 빼면 이런 균일한 밝기 변화는 상쇄되고, 실제 국소적
    변화(물건이 놓이는 것)만 남는다."""
    prev_norm = prev_gray_small.astype(np.float32) - float(prev_gray_small.mean())
    curr_norm = gray_small.astype(np.float32) - float(gray_small.mean())
    diff = np.abs(curr_norm - prev_norm)
    return diff > MOTION_DIFF_THRESHOLD


def bbox_to_grid_mask(
    bbox_px: tuple[int, int, int, int] | None, frame_shape: tuple[int, int]
) -> np.ndarray:
    """픽셀 좌표 bbox를 그리드 좌표계의 bool 마스크로 변환한다(제외 영역 표시용)."""
    mask = np.zeros((GRID_ROWS, GRID_COLS), dtype=bool)
    if bbox_px is None:
        return mask
    h, w = frame_shape
    x0, y0, x1, y1 = bbox_px

    gx0, gx1 = int(x0 / w * GRID_COLS), int(x1 / w * GRID_COLS)
    gy0, gy1 = int(y0 / h * GRID_ROWS), int(y1 / h * GRID_ROWS)
    mask[max(0, gy0) : min(GRID_ROWS, gy1), max(0, gx0) : min(GRID_COLS, gx1)] = True
    return mask


def largest_candidate_region(
    candidate_mask: np.ndarray, exclude: np.ndarray
) -> tuple[int, int, int, int] | None:
    """candidate_mask(그리드, bool: "막 멈춘" 블록) 중 exclude 아닌 영역에서 가장 큰 연결
    성분의 (gx0, gy0, gx1, gy1) 그리드 bbox. 최소 크기 미만이면 None."""
    candidate = (candidate_mask & ~exclude).astype(np.uint8)
    if candidate.sum() == 0:
        return None

    # 조명 플리커/머리카락 질감 등이 만드는 고립된 1칸짜리 노이즈를 제거한다 -- 3x3
    # 이웃(자기 포함 9칸) 중 후보가 NEIGHBOR_VOTE_MIN칸 미만이면 노이즈로 보고 지운다.
    # (처음엔 cv2.erode(3x3)를 썼는데 너무 공격적이라 작은 소품 후보까지 통째로 사라지는
    # 문제가 합성 테스트로 확인됐다 -- "이웃 투표" 방식은 고립 노이즈는 여전히 지우면서
    # 작은 소품 블록은 거의 그대로 살린다.)
    neighbor_count = cv2.filter2D(
        candidate.astype(np.float32),
        -1,
        np.ones((3, 3), np.float32),
        borderType=cv2.BORDER_CONSTANT,
    )
    # 자기 자신이 원래 후보가 아니었으면 이웃표가 많아도 후보로 승격시키지 않는다
    # (안 그러면 뭉친 블록 가장자리 바로 바깥 칸까지 "이웃이 많다"는 이유로 새로 후보가
    # 되어 영역이 사방으로 부풀어버린다 -- 합성 테스트로 발견).
    candidate = (candidate.astype(bool) & (neighbor_count >= NEIGHBOR_VOTE_MIN)).astype(np.uint8)
    if candidate.sum() == 0:
        return None

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    if num_labels <= 1:
        return None

    # 배경(label 0) 제외하고 가장 큰 성분
    areas = stats[1:, cv2.CC_STAT_AREA]
    best_label = int(np.argmax(areas)) + 1
    area = stats[best_label, cv2.CC_STAT_AREA]
    grid_area = GRID_COLS * GRID_ROWS
    if area < MIN_STILL_AREA_FRAC * grid_area or area > MAX_STILL_AREA_FRAC * grid_area:
        return None

    x, y, w, h = (
        stats[best_label, cv2.CC_STAT_LEFT],
        stats[best_label, cv2.CC_STAT_TOP],
        stats[best_label, cv2.CC_STAT_WIDTH],
        stats[best_label, cv2.CC_STAT_HEIGHT],
    )
    return x, y, x + w, y + h


def crop_around_bbox(frame: np.ndarray, bbox_px: tuple[int, int, int, int]) -> np.ndarray:
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = bbox_px
    pad_x = int((x1 - x0) * CROP_PADDING_FRAC)
    pad_y = int((y1 - y0) * CROP_PADDING_FRAC)
    x0, y0 = max(0, x0 - pad_x), max(0, y0 - pad_y)
    x1, y1 = min(w, x1 + pad_x), min(h, y1 + pad_y)
    return frame[y0:y1, x0:x1]


def embed_image(classifier, image_path: Path):
    """분류기가 이미 갖고 있는 `_embed()`(이미지+텍스트 인코딩)를 재사용해 이미지
    임베딩만 뽑는다. 텍스트는 API를 맞추기 위한 더미 1개만 넣고 버린다."""
    image_embeds, _ = classifier._embed(image_path, ["product"])
    return image_embeds[0]  # (D,) L2-정규화됨


def main():
    print(f"=== 카테고리 분류기 로드 ({CATEGORY_BACKEND}, 중복 감지용) ===")
    t0 = time.time()
    classifier = get_category_classifier(CATEGORY_BACKEND)
    print(f"완료 ({time.time() - t0:.1f}s)")

    print(f"=== 포즈 모델 로드 ({POSE_MODEL}, 몸통 제외 영역 계산용) ===")
    t0 = time.time()
    pose_model = YOLO(POSE_MODEL)
    print(f"완료 ({time.time() - t0:.1f}s)")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"카메라 {CAMERA_INDEX}를 열 수 없습니다")

    prev_gray_small = None
    seconds_since_motion = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.float32)
    start_time = time.time()
    last_loop_time = start_time
    last_trigger_time = 0.0
    last_face_bbox: tuple[int, int, int, int] | None = None
    last_face_time = -FACE_STALE_SECONDS
    shot_count = 0
    registered_count = 0
    registered_embeddings: list = []
    registered_labels: list[str] = []
    registered_categories: list[str] = []

    print("\n=== 실행 중 (창에 포커스한 뒤 'q'로 종료) ===")
    print(
        f"상품을 카메라 앞에 갖다 대고 {STABLE_SECONDS_REQUIRED:.1f}초 이상 멈춰 있으면 자동으로 캡처됩니다."
    )

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("프레임을 읽지 못했습니다")
                break

            h, w = frame.shape[:2]
            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_small = cv2.resize(gray_full, (GRID_COLS, GRID_ROWS))

            now = time.time()
            dt = max(0.0, now - last_loop_time)
            last_loop_time = now
            in_cooldown = (now - last_trigger_time) < COOLDOWN_SEC

            display = frame.copy()
            triggered = False

            if prev_gray_small is not None:
                moved = grid_motion_mask(prev_gray_small, gray_small)
                seconds_since_motion[moved] = 0.0
                seconds_since_motion[~moved] += dt

            past_startup = (now - start_time) > STARTUP_GRACE_SECONDS

            if prev_gray_small is not None and not in_cooldown and past_startup:
                # "막 멈춘" 블록만 후보로 잡는다 -- 오래 정지해 있던 배경은 STABLE_SECONDS_MAX_AGE를
                # 넘어가면서 자동으로 후보에서 빠진다.
                candidate_mask = (seconds_since_motion >= STABLE_SECONDS_REQUIRED) & (
                    seconds_since_motion <= STABLE_SECONDS_MAX_AGE
                )
                face_bbox = detect_face_bbox(gray_full)
                if face_bbox is not None:
                    last_face_bbox, last_face_time = face_bbox, now
                elif now - last_face_time <= FACE_STALE_SECONDS:
                    face_bbox = last_face_bbox  # 방금까지 있던 얼굴 위치를 잠깐 우려먹는다
                torso_bbox = detect_torso_bbox(pose_model, frame)
                exclude = bbox_to_grid_mask(face_bbox, (h, w)) | bbox_to_grid_mask(
                    torso_bbox, (h, w)
                )

                region = largest_candidate_region(candidate_mask, exclude)

                # 시각화: 후보 블록을 반투명하게 표시
                overlay = display.copy()
                for gy in range(GRID_ROWS):
                    for gx in range(GRID_COLS):
                        if candidate_mask[gy, gx] and not exclude[gy, gx]:
                            x0, y0 = int(gx / GRID_COLS * w), int(gy / GRID_ROWS * h)
                            x1, y1 = int((gx + 1) / GRID_COLS * w), int((gy + 1) / GRID_ROWS * h)
                            cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 255), -1)
                display = cv2.addWeighted(overlay, 0.25, display, 0.75, 0)

                if face_bbox is not None:
                    cv2.rectangle(display, face_bbox[:2], face_bbox[2:], (255, 0, 0), 2)
                if torso_bbox is not None:
                    cv2.rectangle(display, torso_bbox[:2], torso_bbox[2:], (255, 0, 255), 2)

                if region is not None:
                    gx0, gy0, gx1, gy1 = region
                    bbox_px = (
                        int(gx0 / GRID_COLS * w),
                        int(gy0 / GRID_ROWS * h),
                        int(gx1 / GRID_COLS * w),
                        int(gy1 / GRID_ROWS * h),
                    )
                    cv2.rectangle(display, bbox_px[:2], bbox_px[2:], (0, 255, 0), 2)
                    cv2.putText(
                        display,
                        "captured!",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2,
                    )

                    crop = crop_around_bbox(frame, bbox_px)
                    if crop.size > 0:
                        shot_count += 1
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        crop_path = os.path.join(OUT_DIR, f"crop_{timestamp}_{shot_count}.png")
                        frame_path = os.path.join(OUT_DIR, f"frame_{timestamp}_{shot_count}.png")
                        cv2.imwrite(crop_path, crop)
                        cv2.imwrite(frame_path, display)

                        print(f"\n=== 캡처 #{shot_count} -> {crop_path} ===")
                        print("분류 중(VLM)...")
                        t0 = time.time()
                        predicted, raw_text = query_category(Path(crop_path))
                        elapsed = time.time() - t0
                        if predicted is None:
                            print(f"분류 실패({elapsed:.2f}s): 목록에 없는 응답 -- {raw_text!r}")
                            predicted = "UNKNOWN"
                        label_kr = _KR_LABELS.get(predicted, predicted)
                        print(f"분류 결과({elapsed:.2f}s): {label_kr} ({predicted})")

                        # 중복 감지: 같은 카테고리로 분류된 것끼리만 임베딩을 비교한다 --
                        # 카테고리가 다르면 임베딩이 우연히 비슷해도 애초에 비교하지 않는다.
                        embedding = embed_image(classifier, Path(crop_path))
                        best_sim, best_idx = -1.0, -1
                        for i, prev in enumerate(registered_embeddings):
                            if registered_categories[i] != predicted:
                                continue
                            sim = float((embedding @ prev).item())
                            if sim > best_sim:
                                best_sim, best_idx = sim, i

                        if best_idx >= 0 and best_sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                            print(
                                f"중복으로 판단(같은 카테고리 {label_kr}, 유사도 {best_sim:.3f} >= "
                                f"{DUPLICATE_SIMILARITY_THRESHOLD}, 기존 #{best_idx + 1}) -- 건너뜁니다"
                            )
                        else:
                            if best_idx >= 0:
                                print(f"(같은 카테고리 내 최고 유사도 {best_sim:.3f} -- 중복 아님)")
                            registered_embeddings.append(embedding)
                            registered_labels.append(label_kr)
                            registered_categories.append(predicted)
                            registered_count += 1

                        last_trigger_time = now
                        triggered = True
            elif in_cooldown:
                remaining = COOLDOWN_SEC - (now - last_trigger_time)
                cv2.putText(
                    display,
                    f"cooldown {remaining:.1f}s",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (128, 128, 128),
                    2,
                )

            if triggered:
                # 방금 캡처한 영역이 쿨다운 뒤에도 여전히 "막 멈춘" 범위에 남아 곧바로
                # 재트리거되는 걸 막는다(카메라 프레임레이트가 낮으면 나이-아웃만으론
                # 부족할 수 있어 안전장치로 명시적으로 리셋).
                seconds_since_motion[:] = STABLE_SECONDS_MAX_AGE + 1.0

            prev_gray_small = gray_small
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
