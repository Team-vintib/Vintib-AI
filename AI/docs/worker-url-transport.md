# 왜 워커 입출력이 전부 URL인가

시착(`user_image_url`/`product_image_url`), 품질검수(`image_urls`), STT(`audio_url`) —
워커가 다루는 무거운 데이터(이미지·오디오)는 전부 job payload에 바이트로 실리지 않고
**URL로만** 오간다. 새 워커를 만들 때마다 매번 같은 질문이 나올 수 있어 이유를 한 곳에
정리해 둔다.

## 이유 1 — 워커는 인바운드 접속을 받을 수 없다

워커는 팀원 노트북이고 공유기 뒤에 있어 **외부에서 워커로 직접 접속(인바운드)이 불가능**하다.
그래서 게이트웨이가 워커에게 데이터를 "밀어넣는(push)" 방식 자체가 성립하지 않는다. 워커가
할 수 있는 건 아웃바운드 요청뿐이라(`worker/README.md`), 데이터를 받는 방법도 "워커가 먼저
URL로 요청해서 끌어온다(pull)"는 형태일 수밖에 없다.

```
[EC2] AI 게이트웨이
        ↑ HTTP 아웃바운드만 가능 (워커 → 게이트웨이)
[노트북] 워커
```

## 이유 2 — Redis 큐에 큰 바이너리를 넣지 않는다

그럼 "job payload 자체에 이미지 바이트를 실어 보내면 안 되나?"도 안 된다.
`infra-architecture.md` §3.3에 명시된 원칙이다:

> job 큐와 결과 임시 캐시 용도로만 사용한다. 이미지 등 큰 바이너리는 절대 담지 않는다(URL만 저장).

`docker-compose.yml`의 Redis엔 `maxmemory 768mb`가 걸려 있다. 여기에 매 job마다 이미지·오디오
바이트를 실으면 큐 전체가 금방 메모리 압박을 받는다. Redis는 "무슨 job인지, 파일이 어디
있는지" 같은 가벼운 제어 정보만 다루도록 설계됐다.

## 그래서 이런 구조가 됐다

- **큐(Redis)**: job 메타데이터(어떤 기능인지, 파일이 어디 있는지)만 이동 — 가볍고 빠름
- **파일 저장소(EC2 로컬 디스크 → URL)**: 실제 무거운 바이트가 머무는 곳 — S3 권한이 없어
  게이트웨이의 `/workers/upload-image`·`/workers/upload-json` 업로드 엔드포인트와 `/results/*`
  정적 서빙으로 대체(`results-access-control.md` 참고)
- **워커**: 필요할 때 그 URL로 직접 가서 끌어옴(아웃바운드 GET이라 인바운드 제약과 무관)

이미지에서 먼저 자리 잡은 패턴이고, 오디오(STT)도 정확히 같은 제약(워커 인바운드 불가,
Redis 바이너리 금지)을 받기 때문에 새로 고안하지 않고 같은 방식(`audio_url`)을 그대로
재사용했다 — `worker/storage_utils.py`의 `download_image`/`download_bytes`가 이 패턴의
공통 구현이다.

## 관련 자료

- `AI/docs/infra-architecture.md` §2(워커 네트워크 제약), §3.3(Redis 원칙)
- `AI/docs/results-access-control.md` — 이렇게 만들어진 결과 URL을 외부에 얼마나 열어둘지
- `worker/README.md`, `worker/storage_utils.py`
