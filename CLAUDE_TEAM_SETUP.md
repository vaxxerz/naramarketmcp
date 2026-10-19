# Claude Team 배포 및 연결

이 포크는 공공 HTTPS 서버의 `/mcp`를 통해 Claude Team에 연결한다.
원본: https://github.com/alphago2580/naramarketmcp (Apache-2.0).

## Render 설정

- 유형: Web Service / Docker, branch: main, region: Singapore
- 요금: Free로 시험 (15분 유휴 시 절전, 재시작 약 1분). 상시 운영은 유료 인스턴스 선택.
- Health Check Path: `/healthz`
- `FASTMCP_TRANSPORT=http`, `FASTMCP_HOST=0.0.0.0` (Docker 이미지 기본값)
- `MCP_ACCESS_TOKEN`: 무작위 접속 토큰. 최소 32자. 서비스 키와 별개이다.
- `NARAMARKET_SERVICE_KEY`: 공공데이터포털 서비스 키. Encoding/Decoding 어느 쪽도 허용한다.

`render.yaml`로 Blueprint 배포도 가능하다. 키를 아직 발급받지 않았다면 대시보드에서
공개 Git 저장소를 연결해 먼저 배포하고, 발급 후 환경변수를 추가해 재배포할 수 있다.
키가 없어도 MCP 초기화, 16개 도구 목록, API 안내 기능은 작동한다.
실제 나라장터 조회는 승인된 서비스 키가 필요하다. `/healthz`는 프로세스 상태만 확인한다.

## 공공데이터포털

먼저 로그인 후 아래 서비스에서 활용신청한다.

- 입찰·낙찰·계약: https://www.data.go.kr/data/15058815/openapi.do
- 통계·물품·쇼핑몰 기능까지 쓰려면 포털에서 아래 서비스도 각각 활용신청한다.
  - 조달청 공공조달통계정보서비스
  - 조달청 나라장터 물품목록정보서비스
  - 조달청 나라장터 종합쇼핑몰 품목정보서비스

승인된 공통 서비스 키를 Render 환경변수에만 저장한다. GitHub, URL, 채팅에는 넣지 않는다.
승인 직후 인증정보 전파가 지연될 수 있다. 신청하지 않은 서비스는 조회에 실패할 수 있다.

## Claude 소유자 등록

1. Organization settings → Connectors → Add → Custom → Web.
2. 이름: `나라장터`, URL: Render 서비스 주소 뒤에 `/mcp`.
3. Authentication: `No sign in` (OAuth를 사용하지 않는 고정 헤더 인증).
4. Request headers: 이름 `Authorization`, 값 `Bearer <MCP_ACCESS_TOKEN>`.
5. Add로 등록하고 팀원이 Customize → Connectors에서 연결한다.

Claude의 모든 팀원이 서버의 공용 공공데이터 키와 호출량을 공유한다.
접속 토큰 교체 시 Render 환경변수와 Claude 조직 커넥터 헤더를 함께 바꾼다.
사용 중인 Claude 화면에 Request headers가 없다면 토큰을 URL에 넣지 말고,
해당 계정에서 제공되는 인증 방식을 확인하거나 OAuth를 별도로 구현해야 한다.

## 검증

```powershell
.venv\Scripts\python.exe -m pytest tests/test_remote_http.py tests/test_utils.py
```

무인증 요청 401, 잘못된 토큰 차단, 헬스 체크, MCP 초기화, 도구 목록,
API 안내 호출, 서비스 키 정규화 및 오류 로그 비노출을 검증한다.
실제 데이터 조회와 Claude 내부 연결 성공은 별도로 확인해야 한다.

공식 문서:
- https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- https://render.com/docs/free
- https://gofastmcp.com/v2/deployment/http
