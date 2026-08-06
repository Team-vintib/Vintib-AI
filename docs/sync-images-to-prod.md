# 로컬 상품 이미지 → 운영 MinIO 동기화

로컬 `vintib-public/products/`에 해당하는 원본 파일들이 `C:\Users\SSAFY\Desktop\products\`
폴더에 있다는 전제다(219개 파일, 51MB 기준). 아래 단계를 그대로 터미널(Git Bash)에서 실행한다.
`I15A108T.pem`은 `C:\Users\SSAFY\Desktop\I15A108T.pem`에 있다는 전제다 — 위치가 바뀌면 아래
경로를 맞게 바꾼다.

## 0. 사전 확인 — 정말 없는지부터 본다

EC2 인스턴스가 새로 발급/교체됐다면 이전에 옮겨둔 이미지가 **그 서버에는 남아있지 않다**
(MinIO 데이터는 `minio-data` 볼륨에 있고, 인스턴스가 바뀌면 볼륨도 새것이다). 재업로드 전에
실제로 없는지 `mc stat`으로 먼저 확인한다 — `mc ls ... | wc -l` 같은 개수 확인은 alias 인증이
조용히 실패해도 오해를 부를 수 있어 신뢰하지 않는다.

```bash
ssh -i "/c/Users/SSAFY/Desktop/I15A108T.pem" ubuntu@i15a108.p.ssafy.io
  
MINIO_USER=$(sudo grep '^MINIO_ROOT_USER=' /home/ubuntu/vintib/.env | cut -d= -f2)
MINIO_PASS=$(sudo grep '^MINIO_ROOT_PASSWORD=' /home/ubuntu/vintib/.env | cut -d= -f2)
echo "USER=[$MINIO_USER]"   # 비어있지 않은지 먼저 확인

sudo docker exec vintib-minio sh -c \
  "mc alias set self http://localhost:9000 '$MINIO_USER' '$MINIO_PASS' && mc stat self/vintib-public/products/1.jpg"
```

`Object does not exist`면 아래 절차로 업로드한다. 실제 객체 정보(크기·수정일)가 나오면 이미
있는 것이니 curl로 공개 URL만 확인하면 된다(맨 아래 "최종 확인" 참고).

## 1. 로컬에서 압축

**반드시 `products` 폴더 안으로 들어가서** 압축한다. 폴더 밖에서 압축하면 압축 해제 시
`products-export/products/...`처럼 한 겹 더 중첩돼 업로드 경로가 틀어진다.

```bash
cd "/c/Users/SSAFY/Desktop/products"
tar -czf "/c/Users/SSAFY/Desktop/products-export.tar.gz" .
```

## 2. EC2로 전송

```bash
scp -i "/c/Users/SSAFY/Desktop/I15A108T.pem" \
  "/c/Users/SSAFY/Desktop/products-export.tar.gz" \
  ubuntu@i15a108.p.ssafy.io:/home/ubuntu/products-export.tar.gz
```

## 3. EC2 접속 후 압축 해제 → 컨테이너로 복사 → mc mirror

```bash
ssh -i "/c/Users/SSAFY/Desktop/I15A108T.pem" ubuntu@i15a108.p.ssafy.io
```

접속 후:

```bash
cd /home/ubuntu
mkdir -p products-export
tar -xzf products-export.tar.gz -C products-export

# ⚠️ /home/ubuntu/vintib/.env는 권한 600 + GitLab 러너 소유라 sudo 없이는 ubuntu 계정으로
#    못 읽는다(docs/infra/ec2.md 참고). sudo 빠뜨리면 MINIO_USER/PASS가 빈 문자열이 되고,
#    mc alias set은 그래도 "Added `self` successfully"를 출력하므로(alias 등록만 하지 인증은
#    바로 검증하지 않는다) 겉보기엔 성공한 것처럼 보이다가 이후 명령이 조용히 실패할 수 있다.
MINIO_USER=$(sudo grep '^MINIO_ROOT_USER=' /home/ubuntu/vintib/.env | cut -d= -f2)
MINIO_PASS=$(sudo grep '^MINIO_ROOT_PASSWORD=' /home/ubuntu/vintib/.env | cut -d= -f2)
echo "USER=[$MINIO_USER]"   # 빈 값이 아닌지 먼저 확인하고 다음으로 넘어간다

docker cp products-export vintib-minio:/tmp/products-export

# 컨테이너 안에서 mc로 vintib-public/products 아래에 업로드(이미 있는 파일은 건드리지 않음)
sudo docker exec vintib-minio sh -c \
  "mc alias set self http://localhost:9000 '$MINIO_USER' '$MINIO_PASS' && \
   mc mirror /tmp/products-export self/vintib-public/products && \
   rm -rf /tmp/products-export"

# 확인은 개수(mc ls | wc -l)가 아니라 stat으로 — 실제 객체 존재를 직접 본다
  sudo docker exec vintib-minio sh -c \
    "mc alias set self http://localhost:9000 '$MINIO_USER' '$MINIO_PASS' && mc stat self/vintib-public/products/1.jpg"
```

## 4. 정리

```bash
rm -rf /home/ubuntu/products-export.tar.gz /home/ubuntu/products-export
exit   # SSH 세션 종료
```

## 5. 최종 확인

로컬 터미널에서 실제 공개 URL을 직접 curl해서 200이 뜨는지 본다 — 이게 가장 확실하다.

```bash
curl -o /dev/null -s -w "%{http_code}\n" "https://i15a108.p.ssafy.io/vintib-public/products/1.jpg"
```

## 참고

- `vintib-public` 버킷 자체가 운영에 없다면(첫 배포 전이면) `mc mirror`가 버킷이 없다는 에러를
  낼 수 있다 — 그 경우 위 명령 전에
  `sudo docker exec vintib-minio sh -c "mc alias set self http://localhost:9000 '$MINIO_USER' '$MINIO_PASS' && mc mb self/vintib-public"`로
  버킷을 먼저 만든다.
- 버킷 정책(익명 읽기)은 `S3BucketInitializer`가 **버킷을 처음 만들 때만** 적용한다
  (`BE/src/main/java/com/ssafy/backend/global/storage/S3BucketInitializer.java`). 버킷이 이미
  존재하면 정책 적용을 건너뛰므로, 오래된 버킷에 정책이 없어 보이면 수동으로 걸어준다:
  `mc anonymous set download self/vintib-public`. 정책 상태는
  `mc anonymous get self/vintib-public`로 확인한다(`custom`이면 이미 우리 정책이 걸려있는 것).
- 운영 DB가 계속 초기화된다고 해도 이미지는 한 번만 옮겨두면 된다 — MinIO 데이터는 DB와 별개
  볼륨이라 DB가 리셋돼도 이미지는 남아있다(볼륨 자체를 지우지 않는 한). 단, **EC2 인스턴스
  자체가 교체되면 볼륨도 새것이라 이미지도 다시 사라진다** — 재현 원인이 애매하면 0번부터
  다시 확인한다.