# otel-langfuse

LangGraph 기반 Teacher-Student 퀴즈 시스템에서 **OpenTelemetry Collector**를 통해 LLM observability 데이터를 Langfuse로 전송합니다.

## 🏗️ 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  LangGraph  │────▶│ OTel         │────▶│   Langfuse   │
│  (FastAPI)  │     │ Collector    │     │   (K8s)      │
│ + Traceloop │     │   (K8s)      │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
      OTLP/gRPC          OTLP/HTTP              │
                              │                 │
                              ▼                 │
                    ┌──────────────┐            │
                    │    Azure     │            │
                    │ Application  │◀───────────┘
                    │  Insights    │   (동일 트레이스)
                    └──────────────┘
                              │
                              ▼
                    ┌──────────────┐
                    │    Azure     │
                    │   Managed    │
                    │   Grafana    │
                    └──────────────┘
```

- **Traceloop SDK**: LangChain/OpenAI 호출을 자동 계측하여 LLM input/output 캡처
- **OTel Collector**: 트레이스를 Langfuse와 Azure Application Insights로 동시 전달
- **Langfuse**: LLM observability 대시보드
- **Azure Application Insights**: 트레이스 저장소
- **Azure Managed Grafana**: 커스텀 대시보드 시각화

## 📁 프로젝트 구조

```
otel-langfuse/
├── main.py              # FastAPI 서버 + OpenTelemetry 초기화
├── graph.py             # LangGraph 워크플로우 (Teacher-Student 퀴즈)
├── config.py            # 환경설정 로드
├── pyproject.toml       # Python 의존성 (uv)
├── templates/
│   └── index.html       # 웹 UI
├── static/
│   └── style.css        # 스타일시트
└── k8s/
    ├── langfuse-values.yaml           # Langfuse Helm values
    ├── otel-collector-values.yaml     # OTel Collector Helm values
    └── azure-grafana-langgraph.json   # Azure Managed Grafana 대시보드
```

## 🚀 시작하기

### 1. 환경 설정

```bash
cp .env.example .env
vim .env
```

### 2. 의존성 설치

```bash
uv sync
```

### 3. 서버 실행

```bash
uv run main.py
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

## ☸️ Kubernetes 배포

### Langfuse 설치

```bash
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm install langfuse langfuse/langfuse -f k8s/langfuse-values.yaml -n langfuse --create-namespace
```

### OpenTelemetry Collector 설치

```bash
# Helm repo 추가
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# OTel Collector 설치
helm install otel-collector open-telemetry/opentelemetry-collector \
    --namespace otel-system --create-namespace \
    --values k8s/otel-collector-values.yaml
```

## 🔧 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 엔드포인트 | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 키 | ✅ |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | 배포 이름 | ❌ (기본: gpt-4o) |
| `AZURE_OPENAI_API_VERSION` | API 버전 | ❌ |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel Collector gRPC 주소 | ❌ (기본: localhost:4317) |

## 📊 Observability 스택

### Traceloop SDK
LangChain, OpenAI 등 LLM 라이브러리를 자동 계측:

```python
from traceloop.sdk import Traceloop
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

Traceloop.init(
    app_name="teacher-student-quiz",
    exporter=OTLPSpanExporter(endpoint="http://otel-collector:4317"),
)
```

### OTel Collector 설정 (k8s/otel-collector-values.yaml)
```yaml
exporters:
  # Langfuse OTLP Exporter
  otlphttp/langfuse:
    endpoint: "http://langfuse-web.langfuse.svc.cluster.local:3000/api/public/otel"
    headers:
      Authorization: "Basic <base64-encoded-credentials>"
  
  # Azure Application Insights Exporter
  azuremonitor:
    connection_string: "<Application-Insights-Connection-String>"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/langfuse, azuremonitor]
```

## 📝 License

MIT

---

## 📊 Azure Managed Grafana 대시보드

Azure Application Insights로 전송된 LangGraph 트레이스를 시각화하는 Grafana 대시보드입니다.

### 대시보드 구성

| 섹션 | 패널 | 설명 |
|------|------|------|
| **Summary** | LangGraph Agent Summary | 전체 트레이스 수, LLM 호출 수, 평균 응답시간, 성공률, 토큰 사용량 |
| **Execution Monitoring** | Agent Execution Trends | 시간별 성공/실패 트렌드 |
| | LLM Call Trends | 시간별 LLM 호출 및 토큰 사용량 |
| **Node Performance** | LangGraph Node Performance | 노드별 실행 횟수, 평균/P95 지연시간, 성공률 |
| | Operation Duration Comparison | 오퍼레이션별 실행시간 비교 |
| **LLM Performance** | LLM Model Performance | 모델/프로바이더별 호출 수, 지연시간, 토큰 사용량 |
| **Sessions** | Recent Agent Sessions | 최근 에이전트 세션 목록 (클릭 시 상세 트레이스 확인) |
| **Execution Flow** | Execution Flow Graph | LangGraph 노드 실행 흐름 시각화 |
| **Trace View** | Agent Execution Trace | 분산 트레이스 타임라인 |
| **Error Analysis** | Recent Errors | TraceId별 에러 그룹화 |

### Span Attributes 매핑

```
Model Name:
  1순위: traceloop.association.properties.ls_model_name (예: gpt-5.2-chat)
  2순위: llm.request.model
  3순위: gen_ai.request.model
  fallback: "unknown"

Provider:
  1순위: traceloop.association.properties.ls_provider (예: azure)
  2순위: gen_ai.system
  fallback: "unknown"

Tokens:
  Total: llm.usage.total_tokens 또는 (gen_ai.usage.input_tokens + gen_ai.usage.output_tokens)
  Input: gen_ai.usage.input_tokens 또는 llm.usage.prompt_tokens
  Output: gen_ai.usage.output_tokens 또는 llm.usage.completion_tokens

LangGraph Node:
  traceloop.association.properties.langgraph_node 또는 name에서 "node_" 접두사 제거
```

### 대시보드 Import 방법

1. **Azure Managed Grafana** 접속
2. 좌측 메뉴 **Dashboards** → **New** → **Import**
3. `k8s/azure-grafana-langgraph.json` 파일 업로드
4. Data Source 선택 후 **Import**

### Template Variables

| 변수 | 설명 |
|------|------|
| `am_ds` | Azure Monitor Data Source |
| `sub` | Azure Subscription |
| `rg` | Resource Group |
| `res` | Application Insights 리소스 |
| `traceId` | 상세 조회할 Trace ID (자동 선택) |
