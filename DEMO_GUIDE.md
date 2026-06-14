# LeaseGuard AI 시연 가이드

본 문서는 다른 PC에서 `LeaseGuard AI` 프로젝트를 내려받아 시연하기 위한 설치 사항, 환경 파일, 실행 명령, 시연 순서를 정리한 문서이다. Windows 11과 PowerShell 기준으로 작성했다.

## 1. 시연 목표

시연에서는 다음 흐름이 정상 동작하는 것을 보여준다.

1. 익명 세션 생성
2. 계약서 TXT/PDF 업로드
3. 계약서 위험요소 분석
4. RAG 기반 계약서 Q&A
5. 답변의 `[Source n]` citation과 source 토글 확인
6. Sequential Multi-Agent 종합 검토 리포트 생성
7. 리포트 저장, 새로고침 복원, 다운로드 확인
8. Dashboard에서 이전 계약서 목록과 채팅 복원 확인

## 2. 필수 설치 사항

시연 PC에는 다음 프로그램이 필요하다.

| 항목 | 권장 버전 | 용도 |
| --- | --- | --- |
| Git | 최신 버전 | 프로젝트 clone |
| Docker Desktop | 최신 버전 | MySQL, ChromaDB 실행 |
| Java JDK | 17 이상 | Spring Boot backend 실행 |
| Node.js | 20 이상 권장 | React frontend 실행 |
| Python | 3.11 이상 권장 | FastAPI RAG server 실행 |
| OpenAI API Key | 사용 가능한 key | Chat API 및 embedding 호출 |

설치 확인 명령은 다음과 같다.

```powershell
git --version
docker --version
java -version
node -v
npm -v
py --version
```

`python` 명령이 동작하지 않는 PC에서는 Windows Python Launcher인 `py` 명령을 사용한다.

## 3. 프로젝트 받기

```powershell
cd D:\
git clone {repository-url} leaseguard-ai
cd D:\leaseguard-ai
```

이미 프로젝트 폴더명이 `leaseguard-ai` 안에 한 번 더 들어가는 구조로 받은 경우, 실제 루트는 다음처럼 확인한다.

```powershell
dir
```

루트에는 다음 파일과 폴더가 있어야 한다.

```text
backend/
frontend/
rag-server/
docker-compose.yml
.env.example
README.md
```

## 4. 환경 변수 설정

루트 디렉터리에서 `.env.example`을 복사해 `.env`를 만든다.

```powershell
copy .env.example .env
notepad .env
```

`.env`의 주요 값은 다음과 같다.

```env
# MySQL
MYSQL_ROOT_PASSWORD=root
MYSQL_DATABASE=leaseguard
MYSQL_USER=leaseguard
MYSQL_PASSWORD=leaseguard123

# Spring Boot
SPRING_DATASOURCE_URL=jdbc:mysql://localhost:3306/leaseguard
SPRING_DATASOURCE_USERNAME=leaseguard
SPRING_DATASOURCE_PASSWORD=leaseguard123
RAG_SERVER_BASE_URL=http://localhost:8000

# FastAPI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=auto
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=128
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

반드시 `OPENAI_API_KEY`를 실제 key로 교체한다. OpenAI key는 frontend에 넣지 않는다.

## 5. Docker 서비스 실행

루트 디렉터리에서 MySQL과 ChromaDB를 실행한다.

```powershell
docker compose up -d mysql chromadb
```

상태 확인:

```powershell
docker ps
```

정상 실행 시 다음 포트가 열려야 한다.

| 서비스 | Host | Port |
| --- | --- | --- |
| MySQL | localhost | 3306 |
| ChromaDB | localhost | 8001 |

컨테이너 로그 확인:

```powershell
docker logs leaseguard-mysql
docker logs leaseguard-chromadb
```

## 6. FastAPI RAG Server 실행

새 PowerShell 터미널을 열고 실행한다.

```powershell
cd D:\leaseguard-ai\rag-server
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

만약 프로젝트가 `D:\leaseguard-ai\leaseguard-ai` 구조라면 다음 경로를 사용한다.

```powershell
cd D:\leaseguard-ai\leaseguard-ai\rag-server
```

FastAPI 상태 확인:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

## 7. reference 문서 인덱싱

FastAPI가 실행 중인 상태에서 새 PowerShell 터미널을 열고 실행한다.

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/rag/references/index"
```

이 단계는 ChromaDB의 `legal_reference` collection에 curated reference 문서를 저장한다. 시연 전 한 번은 반드시 실행한다.

OpenAI embedding을 사용하는 경우 이 단계에서 OpenAI Embedding API가 호출된다. API key가 없거나 호출에 실패하면 local hash embedding fallback이 동작할 수 있으나, 시연 품질은 OpenAI embedding 사용 시 더 안정적이다.

## 8. Spring Boot Backend 실행

새 PowerShell 터미널을 열고 실행한다.

```powershell
cd D:\leaseguard-ai\backend
.\gradlew.bat bootRun
```

프로젝트가 중첩 경로라면 다음을 사용한다.

```powershell
cd D:\leaseguard-ai\leaseguard-ai\backend
.\gradlew.bat bootRun
```

Backend 기본 포트는 `8080`이다.

정상 확인:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/anonymous-sessions"
```

응답 예시는 다음과 같다.

```json
{
  "success": true,
  "data": {
    "anonymousSessionId": "uuid"
  },
  "message": null
}
```

## 9. React Frontend 실행

새 PowerShell 터미널을 열고 실행한다.

```powershell
cd D:\leaseguard-ai\frontend
npm.cmd install
npm.cmd run dev
```

프로젝트가 중첩 경로라면 다음을 사용한다.

```powershell
cd D:\leaseguard-ai\leaseguard-ai\frontend
npm.cmd install
npm.cmd run dev
```

브라우저에서 다음 주소를 연다.

```text
http://localhost:5173
```

## 10. 시연 전 빌드 검증

시간 여유가 있으면 시연 전에 다음 명령으로 빌드를 확인한다.

### 10.1 Backend compile

```powershell
cd D:\leaseguard-ai\backend
.\gradlew.bat compileJava
```

### 10.2 FastAPI compile

```powershell
cd D:\leaseguard-ai\rag-server
.\.venv\Scripts\Activate.ps1
python -m compileall app
```

### 10.3 Frontend build

```powershell
cd D:\leaseguard-ai\frontend
npm.cmd run build
```

## 11. 권장 시연 순서

### 11.1 Home 및 Dashboard 확인

1. `http://localhost:5173`에 접속한다.
2. anonymous session이 자동 생성되는지 확인한다.
3. `My contracts`로 이동해 현재 계약서 목록이 비어 있거나 기존 목록이 표시되는지 확인한다.

### 11.2 계약서 업로드

1. `Start upload` 또는 `Upload contract`를 누른다.
2. TXT 또는 텍스트 추출 가능한 PDF 계약서를 선택한다.
3. `Upload and analyze`를 누른다.
4. 분석 결과 화면으로 이동하는지 확인한다.

시연용 파일은 다음 중 하나를 사용할 수 있다.

```text
data/sample_contracts/
rag-server/data/sample_contracts/
```

폴더가 없거나 샘플 파일이 없는 경우, 간단한 TXT 계약서 파일을 직접 만들어 사용한다.

예시 TXT:

```text
임대인은 계약 종료 후 보증금을 반환한다.
보증금 반환은 신규 임차인이 입주한 이후로 한다.
임차인은 모든 수리비와 원상복구 비용을 부담한다.
특약 사항은 임차인이 모든 관리비와 시설 파손 책임을 부담하는 것으로 한다.
```

### 11.3 분석 결과 확인

분석 결과 화면에서 다음을 확인한다.

- 전체 위험도
- summary
- risk items
- 각 risk item의 description
- 계약서 원문에서 발췌된 evidence

### 11.4 RAG 채팅 확인

`Ask about this contract`를 눌러 채팅 화면으로 이동한다.

권장 질문:

```text
이 계약에서 가장 위험한 점은?
보증금 반환 조건이 위험한지 봐줘
특약 조항 중 임차인에게 불리한 부분이 있어?
임대인에게 뭐라고 물어보면 돼?
짧게 핵심만 말해 줘
```

확인할 부분:

- 답변이 줄바꿈을 유지하는지 확인한다.
- 답변 본문에 `[Source n]`이 표시되는지 확인한다.
- `[Source n]` 버튼을 클릭하면 해당 source가 열리고 강조되는지 확인한다.
- 답변에 source citation이 없는 경우 sources 영역이 표시되지 않는지 확인한다.
- sources가 계약서 근거와 법령/체크리스트 근거로 그룹화되는지 확인한다.

### 11.5 후속 질문과 memory 확인

다음 순서로 질문한다.

```text
이 계약에서 가장 우려되는 점은?
그럼 내가 현실적으로 할 수 있는 일은?
방금 말한 조항을 임대인에게 어떻게 물어봐야 해?
```

확인할 부분:

- “그럼”, “방금 말한 조항” 같은 표현을 이전 대화 맥락으로 이해하는지 확인한다.
- 임대인에게 물어볼 문장 형태로 답변이 나오는지 확인한다.

### 11.6 Sequential Multi-Agent Report 확인

분석 결과 화면으로 돌아가 `Sequential Multi-Agent Report` 영역을 확인한다.

1. `AI 종합 검토 리포트 생성`을 누른다.
2. progress bar가 움직이는지 확인한다.
3. 완료 후 summary와 overall risk가 표시되는지 확인한다.
4. `리포트 본문 보기`를 열어 reportMarkdown이 렌더링되는지 확인한다.
5. `에이전트 검토 과정 보기`를 열어 각 agent 단계가 표시되는지 확인한다.
6. sources 영역을 열어 근거 문장을 확인한다.

### 11.7 리포트 다운로드 확인

리포트 생성 완료 후 다운로드 영역에서 다음을 확인한다.

- Markdown 선택 후 다운로드
- TXT 선택 후 다운로드
- PDF 선택 후 다운로드 버튼 클릭 시 브라우저 인쇄 창 표시

PDF는 서버에서 파일을 생성하는 방식이 아니라 브라우저 `window.print()`를 사용하는 방식이다.

### 11.8 새로고침 복원 확인

1. 리포트가 완료된 상태에서 브라우저를 새로고침한다.
2. 저장된 리포트가 다시 표시되는지 확인한다.
3. Dashboard로 이동했다가 같은 계약서의 분석 결과로 다시 들어와도 리포트가 복원되는지 확인한다.

### 11.9 계약서 삭제와 세션 초기화 확인

Dashboard에서 다음을 확인한다.

- 계약서 삭제 버튼 클릭
- 삭제 후 목록에서 사라지는지 확인
- 삭제된 계약서 분석/채팅 진입이 막히는지 확인
- 세션 초기화 후 새 anonymous session이 생성되는지 확인

## 12. API 직접 테스트 명령

### 12.1 익명 세션 생성

```powershell
$sessionResponse = Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/anonymous-sessions"
$anonymousSessionId = $sessionResponse.data.anonymousSessionId
$anonymousSessionId
```

### 12.2 계약서 목록 조회

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost:8080/api/v1/contracts" `
  -Headers @{ "X-Anonymous-Session-Id" = $anonymousSessionId }
```

### 12.3 FastAPI reference 인덱싱

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/rag/references/index"
```

### 12.4 FastAPI health

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

## 13. 시연 중 자주 발생하는 문제

| 문제 | 해결 |
| --- | --- |
| Docker container가 실행되지 않음 | Docker Desktop이 실행 중인지 확인하고 `docker compose up -d mysql chromadb`를 다시 실행한다. |
| MySQL port 3306 충돌 | 기존 MySQL 서비스를 중지하거나 `docker-compose.yml`의 port를 변경한다. |
| Backend가 DB 연결 실패 | MySQL container가 완전히 뜬 뒤 backend를 실행한다. `.env` 또는 `application.yml`의 DB 값도 확인한다. |
| FastAPI가 ChromaDB 연결 실패 | ChromaDB container와 `CHROMA_HOST=localhost`, `CHROMA_PORT=8001` 설정을 확인한다. |
| OpenAI 호출 실패 | API key, billing, network 상태를 확인한다. Chat은 fallback 답변이 가능하지만 embedding 품질은 낮아질 수 있다. |
| PDF 업로드 실패 | 스캔 PDF는 OCR 미지원이다. 텍스트 선택 가능한 PDF 또는 TXT 파일을 사용한다. |
| PowerShell에서 한글이 깨져 보임 | 콘솔 인코딩 표시 문제일 수 있다. React 화면과 API JSON은 UTF-8 기준으로 처리한다. |
| `npm` 실행 오류 | PowerShell에서는 `npm.cmd install`, `npm.cmd run dev`를 사용한다. |
| `python` 명령 없음 | `py -3` 또는 `.venv\Scripts\python.exe`를 사용한다. |

## 14. 시연 체크리스트

시연 직전 다음 항목을 확인한다.

- [ ] Docker Desktop 실행
- [ ] MySQL container 실행
- [ ] ChromaDB container 실행
- [ ] FastAPI `http://localhost:8000` 실행
- [ ] `/rag/references/index` 실행 완료
- [ ] Spring Boot `http://localhost:8080` 실행
- [ ] React `http://localhost:5173` 실행
- [ ] OpenAI API key 설정
- [ ] TXT 또는 텍스트 기반 PDF 샘플 계약서 준비
- [ ] 브라우저 새로고침 후 anonymous session 생성 확인
- [ ] 리포트 다운로드 테스트용 브라우저 인쇄 권한 확인

## 15. 시연 설명 문장 예시

시연 중 프로젝트를 설명할 때 다음 문장을 사용할 수 있다.

```text
LeaseGuard AI는 임대차계약서의 최종 법률 판단을 대신하는 서비스가 아니라,
계약서에서 확인이 필요한 위험요소를 reference 문서와 비교해 점검하는 RAG 기반 AI 도우미이다.
```

```text
채팅 답변은 계약서 chunk와 reference chunk를 먼저 검색한 뒤 생성되며,
답변에 사용된 근거만 [Source n] 형태로 연결해 사용자가 직접 확인할 수 있게 했다.
```

```text
Sequential Multi-Agent Report는 여러 agent 역할을 순차적으로 실행해
보증금 반환, 특약, 수리비, 전입신고, 등기부등본, 전세사기 예방 항목을 나누어 검토한 뒤 하나의 종합 리포트로 합친다.
```
