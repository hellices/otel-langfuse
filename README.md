# otel-langfuse

LangGraph 기반 Teacher-Student 퀴즈 시스템

1. **LangGraph → Azure Monitor**: 운영 모니터링
2. **Agent Lightning → Azure Monitor**: APO 학습 대시보드

## 🏗️ 아키텍처

```
┌─────────────┐                              ┌──────────────┐
│  LangGraph  │──────┐                 ┌────▶│   Langfuse   │
│  (FastAPI)  │      │                 │     └──────────────┘
└─────────────┘      │      ┌──────────┴───┐
                     ├─────▶│     OTel     │   service.name=
┌─────────────┐      │      │   Collector  │   "teacher-student-quiz"
│   Agent     │──────┘      └──────────┬───┘         │
│  Lightning  │                        │             ▼
│   (APO)     │                        │      ┌──────────────┐     ┌──────────────┐
└─────────────┘                        │      │ App Insights │────▶│   Grafana    │
                                       │      │   (운영)      │     │ (운영 대시보드) │
                     service.name=     │      └──────────────┘     └──────────────┘
                     "agentlightning"  │
                                       ▼
                                ┌──────────────┐     ┌──────────────┐
                                │ App Insights │────▶│   Grafana    │
                                │   (학습)      │     │ (학습 대시보드) │
                                └──────────────┘     └──────────────┘
```

## 🚀 시작하기

```bash
cp .env.example .env    # 환경변수 설정
uv sync                  # 의존성 설치
uv run python run_server.py  # 서버 실행
```

브라우저에서 http://localhost:8000 접속

---

## 1️⃣ LangGraph → Azure Monitor (운영 모니터링)

### Teacher-Student 퀴즈 시스템

LangGraph Multi-Agent 퀴즈:
- **Teacher Agent**: 문제 출제 및 평가
- **Student Agent**: 문제 풀이

### OpenTelemetry 트레이싱

`app/main.py`에서 모든 LangGraph 실행을 자동 트레이싱:

```python
provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "teacher-student-quiz"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT)))
LangchainInstrumentor().instrument()  # LangChain 자동 계측
```

### OTel Collector 라우팅

트레이스를 두 곳으로 동시 전송:
- **Langfuse**: LLM observability (프롬프트, 토큰, 비용)
- **Azure Application Insights**: APM (지연시간, 에러율, 분산 추적)

### Grafana 운영 대시보드

**대시보드**: `k8s/azure-grafana-langgraph.json`
- 트레이스 수, LLM 호출 수, 토큰 사용량
- 노드별 지연시간 및 성공률
- 모델별 성능 비교

---

## 2️⃣ Agent Lightning → Azure Monitor (APO 학습 대시보드)

APO (Automatic Prompt Optimization)로 Student 프롬프트를 최적화합니다.

### 학습 실행

```bash
uv run python run_training.py
```

### 학습 구성

- **Agent**: `training/agent.py` - Student 프롬프트 최적화
- **Evaluator**: `training/evaluator.py` - LLM-as-Judge 평가
- **Dataset**: `training/dataset.py` - 27개 문제
- **Prompts**: `app/prompts.yaml` - 공유 프롬프트

### 학습 트레이싱

Agent Lightning 트레이스를 Azure Application Insights로 전송:

```python
class OtelTracerWithExporter(agl.OtelTracer):
    def _initialize_tracer_provider(self, worker_id: int):
        super()._initialize_tracer_provider(worker_id)
        if self._tracer_provider:
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT))
            )
```

### Grafana 학습 대시보드

**대시보드**: `k8s/azure-grafana-agentlightning.json`
- Rollout 수, Success Rate, Avg Reward
- 시간별 Reward 추이

---

## ☸️ Kubernetes 배포

### Langfuse

```bash
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm install langfuse langfuse/langfuse -f k8s/langfuse-values.yaml -n langfuse --create-namespace
```

### OpenTelemetry Collector

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm install otel-collector open-telemetry/opentelemetry-collector \
    -f k8s/otel-collector-values.yaml -n otel-system --create-namespace
```

## 🔧 환경 변수

| 변수 | 설명 |
|------|------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 키 |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | 모델 배포명 (기본: gpt-4o) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel Collector 주소 (기본: localhost:4317) |

---

## 📸 참고 이미지

### Langfuse Dashboard
![Langfuse Dashboard](static/langfuse_only.png)

### Azure App Insights + Langfuse
![Azure App Insights + Langfuse](static/otel_azuremonitor_with_langfuse.png)

### Azure Grafana
![Azure Grafana](static/azure_grafana.gif)

---

## 📖 문서

### OpenTelemetry AI Semantic Conventions

대시보드 구성 및 OpenTelemetry GenAI 시맨틱 컨벤션에 대한 상세 가이드:

- **[OpenTelemetry Semantic Conventions 가이드](docs/opentelemetry-semantic-conventions.md)**
  - GenAI Span Attributes 명세
  - Metrics 및 Events 명세
  - 대시보드 구현 분석
  - Kusto 쿼리 예제
