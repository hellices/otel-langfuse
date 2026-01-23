# otel-langfuse

> 🧪 **실험 프로젝트**: Langfuse 직접 전송 → OpenTelemetry Collector 전환 테스트

LangGraph 기반 Teacher-Student 퀴즈 시스템을 사용하여 LLM observability 데이터를 Langfuse로 전송하는 방식을 실험합니다.

## 🎯 목표

| 단계 | 방식 | 상태 |
|------|------|------|
| Phase 1 | Langfuse SDK 직접 전송 | ✅ 완료 |
| Phase 2 | OpenTelemetry Collector 경유 | 🚧 진행 중 |

## 🏗️ 아키텍처

### 현재 (Phase 1) - 직접 전송
```
┌─────────────┐     ┌──────────────┐
│  LangGraph  │────▶│   Langfuse   │
│  (FastAPI)  │     │   (K8s)      │
└─────────────┘     └──────────────┘
```

### 목표 (Phase 2) - OTel Collector 경유
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  LangGraph  │────▶│ OTel         │────▶│   Langfuse   │
│  (FastAPI)  │     │ Collector    │     │   (K8s)      │
└─────────────┘     └──────────────┘     └──────────────┘
```

## 📁 프로젝트 구조

```
otel-langfuse/
├── main.py              # FastAPI 서버 엔트리포인트
├── graph.py             # LangGraph 워크플로우 (Teacher-Student 퀴즈)
├── config.py            # 환경설정 로드
├── requirements.txt     # Python 의존성
├── templates/
│   └── index.html       # 웹 UI
├── static/
│   └── style.css        # 스타일시트
└── k8s/
    └── langfuse-values.yaml.example  # Helm values 템플릿
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# 환경변수 파일 생성
cp .env.example .env

# 값 입력
vim .env
```

### 2. 의존성 설치

```bash
# uv 사용 시
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# pip 사용 시
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
uv run main.py
# 또는
python main.py
```

브라우저에서 http://localhost:8000 접속

## 🎮 데모 앱: Teacher-Student 퀴즈

LangGraph Multi-Agent 시스템으로 구현된 퀴즈 애플리케이션:

- **Teacher Agent**: 문제 출제 및 평가
- **Student Agent**: 문제 풀이 시연

### 사용 예시
```
사용자: "보통 수학 문제"
→ Teacher가 중간 난이도 수학 문제 출제
→ Student가 풀이 과정과 함께 답변
→ Teacher가 정답 여부 평가
```

## ☸️ Langfuse 배포 (Kubernetes)

```bash
# Helm values 파일 생성
cp k8s/langfuse-values.yaml.example k8s/langfuse-values.yaml
vim k8s/langfuse-values.yaml

# Helm 설치
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm install langfuse langfuse/langfuse -f k8s/langfuse-values.yaml -n langfuse
```

## 🔧 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 엔드포인트 | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 키 | ✅ |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | 배포 이름 | ❌ (기본: gpt-4o) |
| `AZURE_OPENAI_API_VERSION` | API 버전 | ❌ |

## 📊 Observability

### Langfuse 연동
현재 `langfuse.langchain.CallbackHandler`를 사용하여 트레이싱:

```python
from langfuse.langchain import CallbackHandler
langfuse_handler = CallbackHandler()
```

### TODO: OTel Collector 전환
- [ ] OpenTelemetry SDK 설정
- [ ] OTel Collector 배포 (K8s)
- [ ] Langfuse OTLP 엔드포인트 연결
- [ ] 트레이스/메트릭 비교 분석

## 📝 License

MIT
