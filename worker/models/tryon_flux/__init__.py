"""FLUX.2-Klein 기반 worn-reference 생성 — `worker/models/sam3`/`quality_vlm`과 같은 이유로
진짜 서브패키지다(`__init__.py` 보유). 여러 워커 패키지가 한 프로세스에 동시에 로드될 때
같은 이름의 파일(registry.py 등)이 flat하게 sys.path에 들어가면 충돌하므로, 부모 디렉터리
(`worker/models/`)를 sys.path에 넣고 `tryon_flux.xxx` 네임스페이스로만 접근한다.
"""
