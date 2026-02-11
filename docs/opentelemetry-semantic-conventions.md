# OpenTelemetry AI Semantic Conventions 가이드

이 문서는 OpenTelemetry AI Semantic Conventions를 기반으로 대시보드를 구성하고, 이 프로젝트의 대시보드가 어떻게 설계되었는지 설명합니다.

## 📚 목차

1. [OpenTelemetry GenAI Semantic Conventions 개요](#opentelemetry-genai-semantic-conventions-개요)
2. [핵심 Span Attributes](#핵심-span-attributes)
3. [Metrics 명세](#metrics-명세)
4. [Events 명세](#events-명세)
5. [대시보드 구현 분석](#대시보드-구현-분석)
6. [대시보드 생성 가이드](#대시보드-생성-가이드)

---

## OpenTelemetry GenAI Semantic Conventions 개요

OpenTelemetry는 GenAI(Generative AI) 시스템의 관측성(Observability)을 표준화하기 위한 시맨틱 컨벤션을 정의합니다. 이를 통해 다양한 LLM 제공자, 모델, 플랫폼 간의 일관된 텔레메트리 데이터 수집이 가능합니다.

### 참조 링크
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [GitHub: Semantic Conventions](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/README.md)

---

## 핵심 Span Attributes

### 기본 식별자 Attributes

| Attribute | Type | 필수 | 설명 | 예시 |
|-----------|------|------|------|------|
| `gen_ai.system` | string | ✅ | GenAI 제공자/시스템 | `"openai"`, `"azure_openai"`, `"anthropic"` |
| `gen_ai.operation.name` | string | ✅ | 작업 유형 | `"chat"`, `"text_completion"`, `"embeddings"` |
| `gen_ai.request.model` | string | ✅ | 요청된 모델명 | `"gpt-4"`, `"gpt-4-turbo"`, `"claude-3-opus"` |
| `gen_ai.response.model` | string | 권장 | 실제 응답한 모델명 | `"gpt-4-0613"` |
| `gen_ai.response.id` | string | 권장 | 응답 고유 식별자 | `"chatcmpl-abc123"` |

### 요청 파라미터 Attributes

| Attribute | Type | 설명 | 예시 |
|-----------|------|------|------|
| `gen_ai.request.max_tokens` | int | 최대 생성 토큰 수 | `1000` |
| `gen_ai.request.temperature` | float | 창의성 조절 온도 | `0.7` |
| `gen_ai.request.top_p` | float | Nucleus sampling 파라미터 | `0.9` |
| `gen_ai.request.stop_sequences` | string[] | 생성 중단 시퀀스 | `["\n\n"]` |
| `gen_ai.request.presence_penalty` | float | 반복 방지 패널티 | `0.0` |
| `gen_ai.request.frequency_penalty` | float | 빈도 패널티 | `0.0` |

### 토큰 사용량 Attributes

| Attribute | Type | 필수 | 설명 | 예시 |
|-----------|------|------|------|------|
| `gen_ai.usage.input_tokens` | int | ✅ | 입력 토큰 수 | `120` |
| `gen_ai.usage.output_tokens` | int | ✅ | 출력 토큰 수 | `300` |
| `gen_ai.token.type` | string | ✅ (메트릭용) | 토큰 유형 | `"input"`, `"output"` |

### 응답 Attributes

| Attribute | Type | 설명 | 예시 |
|-----------|------|------|------|
| `gen_ai.response.finish_reasons` | string[] | 생성 종료 이유 | `["stop"]`, `["length"]`, `["tool_calls"]` |

### Span 명명 규칙

```
{gen_ai.operation.name} {gen_ai.request.model}
```

**예시:**
- `chat gpt-4`
- `text_completion claude-3-opus`
- `embeddings text-embedding-ada-002`

### Span Kind

- **CLIENT**: 외부 LLM API 호출 시
- **INTERNAL**: 프로세스 내부에서 LLM 실행 시

---

## Metrics 명세

### 클라이언트 메트릭

#### `gen_ai.client.token.usage` (Histogram)

토큰 사용량을 히스토그램으로 측정합니다.

| 속성 | Type | 필수 | 설명 |
|------|------|------|------|
| `gen_ai.operation.name` | string | ✅ | 작업 유형 |
| `gen_ai.request.model` | string | ✅ | 요청된 모델 |
| `gen_ai.system` | string | ✅ | AI 시스템 |
| `gen_ai.token.type` | string | ✅ | `"input"` 또는 `"output"` |
| `gen_ai.response.model` | string | 권장 | 응답 모델 |

**권장 버킷 경계:**
```
[1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]
```

#### `gen_ai.client.operation.duration` (Histogram)

작업 지연시간을 히스토그램으로 측정합니다.

| 속성 | Type | 필수 | 설명 |
|------|------|------|------|
| `gen_ai.operation.name` | string | ✅ | 작업 유형 |
| `gen_ai.request.model` | string | ✅ | 요청된 모델 |
| `gen_ai.system` | string | ✅ | AI 시스템 |

### 서버 메트릭 (LLM 서빙용)

| 메트릭 | Type | 설명 |
|--------|------|------|
| `gen_ai.server.request.duration` | Histogram | 서버 요청 처리 시간 |
| `gen_ai.server.time_per_output_token` | Histogram | 출력 토큰당 처리 시간 |
| `gen_ai.server.time_to_first_token` | Histogram | 첫 토큰까지의 시간 |

---

## Events 명세

GenAI 이벤트는 LLM 상호작용의 입력, 출력, 상태를 캡처합니다.

### 메시지 이벤트

| Event | 설명 | 주요 속성 |
|-------|------|----------|
| `gen_ai.system.message` | 시스템 프롬프트 | `gen_ai.system.message.content` |
| `gen_ai.user.message` | 사용자 입력 | `gen_ai.user.message.content` |
| `gen_ai.assistant.message` | AI 응답 | `gen_ai.assistant.message.content` |
| `gen_ai.tool.message` | 도구 실행 결과 | `gen_ai.tool.message.content` |

### 선택 이벤트

| Event | 설명 |
|-------|------|
| `gen_ai.choice` | AI의 응답 선택 (이유, 메타데이터 포함) |

---

## 대시보드 구현 분석

### 현재 프로젝트의 대시보드

이 프로젝트는 두 개의 Grafana 대시보드를 제공합니다:

1. **LangGraph 운영 대시보드** (`k8s/azure-grafana-langgraph.json`)
2. **Agent Lightning 학습 대시보드** (`k8s/azure-grafana-agentlightning.json`)

### OpenTelemetry Semantic Conventions 적용 현황

#### ✅ 적용된 Conventions

| Convention | 대시보드 사용 | 쿼리 예시 |
|------------|--------------|----------|
| `gen_ai.usage.input_tokens` | LLM Metrics 패널 | `customDimensions['gen_ai.usage.input_tokens']` |
| `gen_ai.usage.output_tokens` | Token Usage 패널 | `customDimensions['gen_ai.usage.output_tokens']` |
| `gen_ai.request.model` | LLM Model Performance | `customDimensions['gen_ai.request.model']` |

#### 하위 호환성

대시보드는 다양한 계측 라이브러리와의 호환성을 위해 `coalesce()` 함수를 사용합니다:

```kusto
// OpenTelemetry 표준과 LangChain 계측 모두 지원
Input = sum(toint(coalesce(
    customDimensions['gen_ai.usage.input_tokens'],      -- OTel GenAI 표준
    customDimensions['llm.usage.prompt_tokens'],        -- 이전 LangChain 계측
    "0"
)))
```

### LangGraph 대시보드 패널 분석

| 패널 | 사용 Attributes | GenAI Convention 적합성 |
|------|----------------|------------------------|
| Overview | `operation_Id`, `duration`, `success` | ✅ 일반 OTel |
| LLM Summary | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` | ✅ GenAI 표준 |
| Token Usage Over Time | `gen_ai.usage.*` | ✅ GenAI 표준 |
| LLM Model Performance | `gen_ai.request.model` | ✅ GenAI 표준 |
| Trace Detail | `operation_Id` | ✅ 일반 OTel |

### Agent Lightning 대시보드 패널 분석

| 패널 | 사용 Attributes | 설명 |
|------|----------------|------|
| Training Overview | `agentlightning.reward.*`, `agentlightning.rollout_id` | 커스텀 학습 메트릭 |
| Reward Trend | `agentlightning.reward.0.value` | APO 최적화 보상 |
| Rollout Summary | `agentlightning.rollout_id`, `agentlightning.attempt_id` | 학습 진행 추적 |

---

## 대시보드 생성 가이드

### 1. 기본 LLM 모니터링 패널

#### 총 토큰 사용량

```kusto
dependencies
| where name has_any ("ChatOpenAI", "AzureChatOpenAI", "openai", "llm", "gen_ai", "chat")
| summarize
    ['LLM Calls'] = count(),
    ['Input Tokens'] = sum(toint(coalesce(
        customDimensions['gen_ai.usage.input_tokens'],
        customDimensions['llm.usage.prompt_tokens'],
        "0"
    ))),
    ['Output Tokens'] = sum(toint(coalesce(
        customDimensions['gen_ai.usage.output_tokens'],
        customDimensions['llm.usage.completion_tokens'],
        "0"
    ))),
    ['Avg LLM Latency (s)'] = round(avg(duration) / 1000, 2)
```

#### 시간별 토큰 사용량 추이

```kusto
dependencies
| where name has_any ("ChatOpenAI", "AzureChatOpenAI", "openai", "llm", "gen_ai", "chat")
| summarize 
    Input = sum(toint(coalesce(
        customDimensions['gen_ai.usage.input_tokens'],
        customDimensions['llm.usage.prompt_tokens'],
        "0"
    ))),
    Output = sum(toint(coalesce(
        customDimensions['gen_ai.usage.output_tokens'],
        customDimensions['llm.usage.completion_tokens'],
        "0"
    )))
    by bin(timestamp, 1m)
```

#### 모델별 성능 분석

```kusto
dependencies
| where name has_any ("ChatOpenAI", "AzureChatOpenAI", "openai", "llm", "gen_ai", "chat")
| extend model = coalesce(
    tostring(customDimensions['gen_ai.request.model']),
    tostring(customDimensions['llm.request.model']),
    tostring(customDimensions['model']),
    "unknown"
)
| summarize 
    Calls = count(),
    ['Avg (s)'] = round(avg(duration) / 1000, 2),
    ['P95 (s)'] = round(percentile(duration, 95) / 1000, 2),
    ['Input Tokens'] = sum(toint(coalesce(
        customDimensions['gen_ai.usage.input_tokens'],
        customDimensions['llm.usage.prompt_tokens'],
        "0"
    ))),
    ['Output Tokens'] = sum(toint(coalesce(
        customDimensions['gen_ai.usage.output_tokens'],
        customDimensions['llm.usage.completion_tokens'],
        "0"
    )))
    by Model = model
| order by Calls desc
```

### 2. 비용 분석 패널 (새로 추가 가능)

토큰 사용량을 기반으로 LLM 비용을 추정할 수 있습니다:

```kusto
let pricing = datatable(model:string, input_per_1k:real, output_per_1k:real) [
    "gpt-4", 0.03, 0.06,
    "gpt-4-turbo", 0.01, 0.03,
    "gpt-3.5-turbo", 0.0015, 0.002
];
dependencies
| where name has_any ("ChatOpenAI", "AzureChatOpenAI", "openai")
| extend model = coalesce(
    tostring(customDimensions['gen_ai.request.model']),
    "gpt-4"
)
| extend input_tokens = toint(coalesce(
    customDimensions['gen_ai.usage.input_tokens'],
    "0"
))
| extend output_tokens = toint(coalesce(
    customDimensions['gen_ai.usage.output_tokens'],
    "0"
))
| lookup kind=leftouter pricing on model
| extend cost = (input_tokens * input_per_1k / 1000) + (output_tokens * output_per_1k / 1000)
| summarize ['Total Cost ($)'] = round(sum(cost), 4) by bin(timestamp, 1h)
```

### 3. 에이전트 흐름 분석 패널

LangGraph 노드 실행 흐름을 시각화합니다:

```kusto
dependencies
| where operation_Id == "<trace_id>"
| where name endswith ".task"
| order by timestamp asc
| extend seq = row_number()
| project 
    id = tostring(seq),
    title = name,
    subtitle = strcat(round(duration, 0), " ms"),
    mainstat = round(duration, 0),
    arc__success = iff(success == "True", 1.0, 0.0),
    arc__failed = iff(success == "False", 1.0, 0.0)
```

### 4. 에러 분석 패널

```kusto
exceptions
| summarize 
    Errors = count(),
    ['Unique Types'] = dcount(type)
    by bin(timestamp, 5m)
```

### 5. 대시보드 구성 권장 사항

#### 섹션 구성

1. **Overview (개요)**
   - Total Traces, Spans, Success Rate
   - Avg Latency, Error Count

2. **Trends (추이)**
   - Request Volume Over Time
   - Latency Percentiles (P50, P95, P99)

3. **LLM Metrics (LLM 메트릭)**
   - Token Usage Summary
   - Token Usage Over Time
   - Model Performance Comparison

4. **Operations (작업)**
   - Top Operations by Count
   - Slowest Operations
   - Operation Success Rate

5. **Traces (트레이스)**
   - Recent Traces Table
   - Trace Waterfall View
   - Task Execution Flow

6. **Errors (에러)**
   - Error Trends
   - Errors by Type
   - Recent Exceptions

---

## 추가 권장 사항

### 1. 누락된 GenAI Attributes 추가 고려

현재 구현에서 추가할 수 있는 속성:

```python
# app/main.py에서 span에 추가 속성 설정
span.set_attribute("gen_ai.system", "azure_openai")
span.set_attribute("gen_ai.operation.name", "chat")
span.set_attribute("gen_ai.request.temperature", 0.7)
span.set_attribute("gen_ai.response.finish_reasons", ["stop"])
```

### 2. 비용 추적을 위한 속성 추가

```python
# 비용 계산 후 span에 기록
estimated_cost = calculate_cost(input_tokens, output_tokens, model)
span.set_attribute("gen_ai.usage.cost", estimated_cost)
```

### 3. 프롬프트 품질 모니터링

```python
# 프롬프트와 응답 품질 지표
span.set_attribute("gen_ai.prompt.template.name", "teacher_question")
span.set_attribute("gen_ai.prompt.version", "v1.0")
```

---

## 결론

이 프로젝트의 대시보드는 OpenTelemetry GenAI Semantic Conventions를 잘 따르고 있습니다:

✅ **강점:**
- `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` 사용
- `gen_ai.request.model` 기반 모델 성능 분석
- 하위 호환성을 위한 `coalesce()` 패턴 사용

📈 **개선 가능 영역:**
- `gen_ai.system`, `gen_ai.operation.name` 속성 명시적 설정
- `gen_ai.response.finish_reasons` 추적 추가
- 비용 추적 메트릭 구현

이 가이드를 참고하여 추가 대시보드 패널을 구성하거나, 기존 대시보드를 확장할 수 있습니다.
