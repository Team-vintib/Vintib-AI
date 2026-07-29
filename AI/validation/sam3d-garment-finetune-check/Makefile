# sam3d-garment-finetune-check
#
# ⚠️ Windows 개발 노트북에는 make 가 없다. 그 환경에서는 각 타깃의 명령을 직접 실행하면 된다 —
#    README "make 없이 실행하기" 참고. 명령이 한 줄씩만 있는 이유도 그래서다.

PYTHON ?= python

.PHONY: help test test-fast lint fmt smoke audit sft dpo clean

help:
	@echo "test      - 전 테스트 (외부 데이터/GPU 불필요)"
	@echo "test-fast - torch 필요 테스트를 건너뛰고 순수 로직만"
	@echo "lint      - ruff check + black --check (AI/pyproject.toml 설정을 따른다)"
	@echo "fmt       - black 자동 정렬"
	@echo "smoke     - 더미 엔드투엔드 (전처리→렌더→I2V→평가→리포트)"
	@echo "audit     - 샘플별 감독 가능성 점검"
	@echo "sft / dpo - 더미 1~2 step 학습 스모크 (torch 필요)"
	@echo "clean     - artifacts/ 와 캐시 삭제"

test:
	$(PYTHON) -m pytest tests -q

test-fast:
	$(PYTHON) -m pytest tests -q -p no:cacheprovider -k "not smoke"

lint:
	cd ../.. && $(PYTHON) -m ruff check validation/sam3d-garment-finetune-check
	cd ../.. && $(PYTHON) -m black --check validation/sam3d-garment-finetune-check

fmt:
	cd ../.. && $(PYTHON) -m black validation/sam3d-garment-finetune-check

smoke:
	$(PYTHON) -m garment3d.cli --config configs/default.yaml --work-dir artifacts/work smoke

audit:
	$(PYTHON) -m garment3d.cli --config configs/default.yaml --work-dir artifacts/work audit

sft:
	$(PYTHON) -m garment3d.cli --config configs/default.yaml --set sft.max_steps=2 --set sft.log_every=1 sft

dpo:
	$(PYTHON) -m garment3d.cli --config configs/default.yaml --set dpo.max_steps=2 --set dpo.min_margin=0.0 dpo

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['artifacts', '.pytest_cache']]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
