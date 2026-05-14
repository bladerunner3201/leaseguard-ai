# LeaseGuard AI

LeaseGuard AI는 임대차계약서를 업로드하면 계약서의 주요 위험요소를 법령 및 공공 체크리스트와 비교해 점검하는 RAG 기반 AI 도우미입니다.

이 서비스는 법률 자문을 대체하지 않습니다. 계약 체결 여부, 위법 여부, 분쟁 승패 가능성을 단정하지 않고, 확인이 필요한 위험요소와 참고 근거를 안내하는 것을 목표로 합니다.

## 기술 스택

- Frontend: React, Vite
- Backend: Spring Boot, Java 17, Gradle
- RAG Server: FastAPI, Python
- Vector DB: ChromaDB
- Database: MySQL
- LLM: OpenAI API
- Infra: Docker, docker-compose

## 아키텍처

```text
[React Frontend]
      |
      | REST API
      v
[Spring Boot Backend]
      |
      | Internal REST API
      v
[FastAPI RAG Server]
      |
      | Vector Search
      v
[ChromaDB]

[MySQL]
```

React는 OpenAI API 또는 FastAPI를 직접 호출하지 않습니다. 모든 요청은 React → Spring Boot → FastAPI → OpenAI API 흐름을 따릅니다.

## 주요 기능

- 익명 세션 기반 사용자 흐름
- 계약서 업로드
- 계약서 텍스트 추출 및 chunking
- ChromaDB 기반 계약서 및 법령/체크리스트 검색
- 계약서 위험요소 분석
- 계약서 기반 Q&A
- 답변 근거 출처 표시
- 채팅 기록 저장

## 레포 구조

```text
leaseguard-ai/
├── frontend/
├── backend/
├── rag-server/
├── data/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 실행 방법

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

`OPENAI_API_KEY`는 FastAPI RAG 서버에서만 사용하며, 프론트엔드에 노출하지 않습니다.

### 2. MySQL 및 ChromaDB 실행

```bash
docker compose up -d mysql chromadb
```

### 3. Backend 실행

```bash
cd backend
gradle bootRun
```

Backend 기본 포트는 `8080`입니다.

### 4. RAG Server 실행

```bash
cd rag-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

RAG Server 기본 포트는 `8000`입니다.

### 5. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

Frontend 기본 포트는 `5173`입니다.

## API 초안

### Anonymous Session

```text
POST /api/v1/anonymous-sessions
```

### Contract

```text
POST /api/v1/contracts
GET /api/v1/contracts
GET /api/v1/contracts/{contractId}
GET /api/v1/contracts/{contractId}/analysis
DELETE /api/v1/contracts/{contractId}
```

### Chat

```text
POST /api/v1/chat-sessions
GET /api/v1/chat-sessions
GET /api/v1/chat-sessions/{chatSessionId}/messages
POST /api/v1/chat-sessions/{chatSessionId}/messages
```

### RAG Server

```text
POST /rag/references/index
POST /rag/contracts/index
POST /rag/chat
```

## 트러블슈팅

- MySQL 포트 충돌 시 `docker-compose.yml`의 외부 포트 `3306`을 변경합니다.
- ChromaDB 포트 충돌 시 외부 포트 `8001`을 변경하고 `CHROMA_PORT`도 함께 수정합니다.
- Spring Boot 실행 전 MySQL 컨테이너가 healthy 상태인지 확인합니다.
- OpenAI API Key는 `.env` 또는 실행 환경 변수로만 설정합니다.

## 향후 발전 방향

- 판례 데이터 추가
- 등기부등본 OCR 분석
- 주소 기반 시세/실거래가 비교
- 위험도 스코어링 고도화
- 변호사/공인중개사 상담 연계
