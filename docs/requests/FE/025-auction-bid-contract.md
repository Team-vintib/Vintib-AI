# 025 입찰 계약 — 남은 FE 항목

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-04

> 입찰(`POST /api/auctions/{auctionId}/bids`)·`BID_PLACED` 이벤트 갱신·실패 코드 처리(A001/A002/A008/A009/A011/W001 등)는
> 반영 완료되어 덜어냈다. `LiveAuctionPanel.vue`가 서버 `nextBidPrice`를 그대로 전송하고, STOMP `BID_PLACED`로 패널을
> 통째로 덮어쓴다. 낙찰 확정·자동 마감은 `030` 참고. 아래 1건만 남는다.

## 남은 항목 — `GET /api/auctions/{auctionId}/bids` 입찰 내역 조회 (미구현)

FE에 `getAuctionBids` 함수도 입찰 내역 UI도 아직 없다(현재 `auctionApi.ts`엔 POST `/bids`만 있음).
**비회원 공개.** 채팅 이력 조회와 같은 커서 페이지네이션이다.

| 파라미터 | 설명 |
| --- | --- |
| `cursor` | 이 `bidId`보다 오래된 입찰을 최신순으로. 첫 페이지는 생략 |
| `size` | 기본 20, 최대 100 |

```jsonc
{
  "content": [
    {
      "bidId": 5001,
      "bidderId": 7,
      "bidderNickname": "빈티지러버",
      "amount": 46000,
      "status": "ACTIVE",       // ACTIVE | OUTBID | WON | LOST
      "createdAt": "2026-08-04T21:40:55",
      "isMine": false           // 토큰 없으면 항상 false
    }
  ],
  "nextCursor": 5000,
  "hasNext": true
}
```

`nextCursor`를 다음 요청에 그대로 넣으면 이어진다.
