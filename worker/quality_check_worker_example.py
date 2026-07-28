from base_worker import BaseWorker


class QualityCheckWorker(BaseWorker):
    feature = "quality_check"

    def run_inference(self, payload: dict) -> dict:
        # payload 예: {"product_image_urls": ["...", "..."]}
        # 1) 이미지 다운로드
        # 2) ViT 기반 오염/하자 판정 모델 호출
        # 3) 결과 리포트 + 점수를 S3/DB에 저장
        # 4) {"score": 0.0~1.0, "defects": [...], "report_url": "..."} 반환
        #    -> 이 결과가 저장되면 가격책정(동기 API)이 이 점수를 조회해서 자동 트리거됨
        raise NotImplementedError("ViT 품질검수 모델을 연결하세요")


if __name__ == "__main__":
    QualityCheckWorker().loop()
