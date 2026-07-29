# FLUX.2 klein 4B 검증

가상 피팅(의류 시착) 기능 후보 모델로 FLUX.2 klein 4B를 검증한 코드입니다.

## 개요

전신 사진 + 의류 이미지를 입력받아 착장 결과를 생성하는 image-to-image 파이프라인으로
FLUX.2 klein 4B(GGUF 양자화)를 테스트했습니다. 검증 결과, 레퍼런스 의류 이미지의 반영
정확도가 낮고(색상/패턴/실루엣이 잘 따라오지 않음), 체형 프롬프트 반영도 불안정하여
최종적으로 CatVTON을 메인 모델로 채택하게 된 근거 자료입니다.

## 파일 설명

| 파일 | 설명 |
|---|---|
| `test_flux.py` | 최초 검증용 스크립트. 텍스트 인코더(Qwen3-4B, 4bit 양자화) + 트랜스포머(GGUF Q4_0) 로드 후 text-to-image 생성 |
| `tryon_fit_aware.py` | person+cloth 2-image 입력 기반 가상 피팅 스크립트. 사이즈 차이(예: S vs XXL)를 규칙 기반으로 계산해 핏 카테고리(tight/fitted/relaxed/oversized)를 프롬프트에 반영하는 로직 포함 |
| `benchmark_flux.py` | steps(4/10/20/30)·해상도(512/1024)별 추론 시간 및 Peak VRAM 측정 스크립트 |
| `flux_benchmark_results.json` | 벤치마크 결과 원본 (RTX 4050 6GB 기준) |
| `requirements_flux.txt` | `pip freeze` 결과. **torch는 CUDA 12.1 빌드로 별도 설치 필요** (아래 참고) |

## 환경 설정

```bash
conda create -n flux-test python=3.10 -y
conda activate flux-test

# torch는 반드시 CUDA 빌드로 명시 설치 (requirements.txt만으론 CPU 버전이 깔릴 수 있음)
pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121

# diffusers는 git 최신판 필요 (Flux2KleinPipeline 지원, pip 정식 릴리스에 없을 수 있음)
pip install git+https://github.com/huggingface/diffusers.git

pip install -r requirements_flux.txt
```

## 실행 방법

`image/person.jpg`, `image/cloth.jpg` 준비 후:

```bash
python tryon_fit_aware.py
```

벤치마크만 실행하려면:

```bash
python benchmark_flux.py
```

## 검증 결과 요약

- **레퍼런스 반영 정확도**: 옷 이미지(색상/패턴/실루엣)와 체형 스펙(키/어깨너비 등) 모두
  텍스트 프롬프트만으로는 안정적으로 반영되지 않음. 특히 person 레퍼런스 이미지가 있을 때
  체형 변경 지시가 거의 무시되는 현상을 반복 실험으로 확인.
- **성능**: steps당 약 11초 (RTX 4050 6GB, CPU 오프로딩 적용 기준). CatVTON 대비 약 4~5배 느림.
  자세한 수치는 `flux_benchmark_results.json` 참고.
- **guidance_scale 무효화**: klein은 step-distilled 모델이라 `guidance_scale` 파라미터가
  무시됨 (경고 메시지로 확인). 텍스트 반영력 조절은 이 파라미터로 불가능.
- **결론**: 범용 image-editing 모델의 구조적 한계로, garment-transfer(의류 전이) 전용
  모델(CatVTON 등) 대비 정확도가 낮음을 확인. 메인 파이프라인은 CatVTON으로 전환.

## 참고

- FLUX.2 klein 4B는 실사 인물 이미지를 다루는 특성상 NCII(비동의 이미지 합성) 방지용
  추론 필터가 모델에 내장되어 있음. 검증 과정에서 별도로 우회하지 않았음.
- Windows 환경에서 `torch==2.4.0`은 `fbgemm.dll` 로딩 실패 버그가 있어 `2.4.1`로 고정 필요
  (PyTorch 공식 이슈 #131662).
