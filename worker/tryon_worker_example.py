from base_worker import BaseWorker


class TryonWorker(BaseWorker):
    feature = "tryon"

    def run_inference(self, payload: dict) -> dict:
        # payload 예: {"user_image_url": "...", "product_image_url": "...", "fit_type": "regular"}
        # 1) 이미지 다운로드
        # 2) CatVTON 파이프라인 호출 (cloth_masker.py 등)
        # 3) 결과 이미지 S3 업로드
        # 4) {"image_url": "..."} 반환
        raise NotImplementedError("CatVTON 추론 코드를 연결하세요")


if __name__ == "__main__":
    TryonWorker().loop()
