"""Agent Lightning RL 학습 스크립트 - APO (Automatic Prompt Optimization)

Azure Application Insights로 상세 학습 trace 전송:
- Rollout 결과 (reward, messages)
- Gradient 계산 과정
- Prompt 편집/최적화 내역
- Beam Search 결과
"""
import os
import json
from pathlib import Path
import sys

# AgentOps 비활성화 (Azure Application Insights로 전송)
os.environ.setdefault("AGENTOPS_API_KEY", "")
os.environ.setdefault("AGENTOPS_LOGGING_LEVEL", "CRITICAL")

from openai import AsyncAzureOpenAI
import agentlightning as agl

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
)

# OtelTracer 환경변수 설정
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", OTEL_EXPORTER_OTLP_ENDPOINT)
os.environ.setdefault("OTEL_EXPORTER_OTLP_INSECURE", "true")
os.environ.setdefault("OTEL_SERVICE_NAME", "agentlightning-training")
os.environ.setdefault("OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT", "65535")
os.environ.setdefault("OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT", "65535")

from training.agent import quiz_agent, initial_prompt_template
from training.dataset import create_dataset

# 학습 상세 로깅을 위한 전역 tracer
_azure_tracer = None
_azure_provider = None


def get_azure_tracer():
    """Azure OTLP tracer 싱글톤"""
    global _azure_tracer, _azure_provider
    if _azure_tracer is None:
        resource = Resource.create({
            "service.name": "agentlightning-training-detail",
            "service.version": "1.0.0",
        })
        _azure_provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        _azure_provider.add_span_processor(BatchSpanProcessor(exporter))
        _azure_tracer = _azure_provider.get_tracer("apo-training")
    return _azure_tracer


def shutdown_azure_tracer():
    """학습 종료 시 TracerProvider flush/shutdown"""
    global _azure_provider
    if _azure_provider is not None:
        _azure_provider.force_flush()
        _azure_provider.shutdown()


class DetailedTrainingHook(agl.Hook):
    """학습 상세 정보를 Azure Application Insights로 전송하는 Hook
    
    추적 정보:
    - 프롬프트 변화 히스토리
    - 라운드별 reward 추이
    - Rollout 상세 결과
    """
    
    def __init__(self, initial_prompt: str):
        self.round_count = 0
        self.rollout_results = []
        self.prompt_history = []  # 프롬프트 변화 기록
        self.initial_prompt = initial_prompt
        self.current_prompt = initial_prompt
        self.best_reward = 0.0
        self.best_prompt = initial_prompt
        
        # 초기 프롬프트 기록
        tracer_inst = get_azure_tracer()
        with tracer_inst.start_as_current_span("prompt.initial") as span:
            span.set_attribute("prompt.version", 0)
            span.set_attribute("prompt.content", initial_prompt[:3000])
            span.set_attribute("prompt.length", len(initial_prompt))
            span.set_attribute("prompt.type", "initial")
        
    async def on_trace_start(self, *, agent, runner, tracer, rollout):
        """Rollout 시작 시 현재 프롬프트 상태 기록"""
        tracer_inst = get_azure_tracer()
        self.round_count += 1
        
        # 현재 리소스에서 프롬프트 추출
        current_prompt = None
        try:
            resources = runner.get_resources() if hasattr(runner, 'get_resources') else {}
            if 'prompt_template' in resources:
                pt = resources['prompt_template']
                current_prompt = pt.template if hasattr(pt, 'template') else str(pt)
        except Exception:
            pass
        
        with tracer_inst.start_as_current_span("rollout.start") as span:
            span.set_attribute("rollout.id", str(rollout.rollout_id) if hasattr(rollout, 'rollout_id') else "unknown")
            span.set_attribute("round.number", self.round_count)
            span.set_attribute("agent.name", agent.__name__ if hasattr(agent, '__name__') else str(agent))
            
            # 현재 프롬프트 상태
            if current_prompt:
                span.set_attribute("prompt.current", current_prompt[:2000])
                span.set_attribute("prompt.changed", current_prompt != self.current_prompt)
                
                # 프롬프트가 변경되었으면 기록
                if current_prompt != self.current_prompt:
                    self.current_prompt = current_prompt
                    self.prompt_history.append({
                        "round": self.round_count,
                        "prompt": current_prompt,
                    })
                    
                    # 프롬프트 변화 span
                    with tracer_inst.start_as_current_span("prompt.updated") as prompt_span:
                        prompt_span.set_attribute("prompt.version", len(self.prompt_history))
                        prompt_span.set_attribute("prompt.content", current_prompt[:3000])
                        prompt_span.set_attribute("prompt.length", len(current_prompt))
                        prompt_span.set_attribute("prompt.round", self.round_count)
    
    async def on_trace_end(self, *, agent, runner, tracer, rollout):
        """Rollout 종료 시 결과 기록"""
        tracer_inst = get_azure_tracer()
        with tracer_inst.start_as_current_span("rollout.end") as span:
            span.set_attribute("rollout.id", str(rollout.rollout_id) if hasattr(rollout, 'rollout_id') else "unknown")
            span.set_attribute("round.number", self.round_count)
    
    async def on_rollout_end(self, *, agent, runner, rollout, spans):
        """각 Rollout 완료 시 상세 span 정보 전송"""
        tracer_inst = get_azure_tracer()
        
        with tracer_inst.start_as_current_span("rollout.result") as parent_span:
            rollout_id = str(rollout.rollout_id) if hasattr(rollout, 'rollout_id') else "unknown"
            parent_span.set_attribute("rollout.id", rollout_id)
            parent_span.set_attribute("round.number", self.round_count)
            parent_span.set_attribute("spans.count", len(spans) if spans else 0)
            
            # 각 span의 상세 정보 추출 및 전송
            rewards = []
            messages = []
            
            for i, span_data in enumerate(spans or []):
                # span 속성 추출
                attrs = getattr(span_data, 'attributes', {}) or {}
                
                # Reward 정보
                if 'agentlightning.reward.value' in attrs:
                    reward_value = attrs.get('agentlightning.reward.value')
                    reward_key = attrs.get('agentlightning.reward.key', 'default')
                    rewards.append({"key": reward_key, "value": reward_value})
                
                # Message 정보 (LLM 응답 등)
                if 'agentlightning.message.body' in attrs:
                    msg_body = attrs.get('agentlightning.message.body', '')
                    messages.append(str(msg_body)[:500])
            
            # 요약 정보 저장
            parent_span.set_attribute("rewards.count", len(rewards))
            parent_span.set_attribute("messages.count", len(messages))
            
            avg_reward = 0.0

            if rewards:
                valid_reward_values = [r['value'] for r in rewards if r['value'] is not None]
                if valid_reward_values:
                    avg_reward = sum(valid_reward_values) / len(valid_reward_values)
                parent_span.set_attribute("rewards.average", avg_reward)
                parent_span.set_attribute("rewards.summary", json.dumps(rewards)[:2000])
                
                # Best 프롬프트 업데이트
                if avg_reward > self.best_reward:
                    self.best_reward = avg_reward
                    self.best_prompt = self.current_prompt
                    
                    with tracer_inst.start_as_current_span("prompt.best_updated") as best_span:
                        best_span.set_attribute("prompt.best_reward", self.best_reward)
                        best_span.set_attribute("prompt.best_content", self.best_prompt[:3000])
                        best_span.set_attribute("prompt.best_round", self.round_count)
            
            # 메시지 샘플 저장 (LLM 응답 확인용)
            if messages:
                parent_span.set_attribute("messages.sample", messages[0][:1000] if messages else "")
            
            self.rollout_results.append({
                "rollout_id": rollout_id,
                "round": self.round_count,
                "rewards": rewards,
                "avg_reward": avg_reward if rewards else 0,
                "messages_count": len(messages),
            })
    
    def get_training_summary(self) -> dict:
        """학습 요약 정보 반환"""
        return {
            "total_rounds": self.round_count,
            "total_rollouts": len(self.rollout_results),
            "prompt_versions": len(self.prompt_history) + 1,  # 초기 포함
            "best_reward": self.best_reward,
            "initial_prompt": self.initial_prompt,
            "best_prompt": self.best_prompt,
            "prompt_history": self.prompt_history,
        }


class OtelTracerWithExporter(agl.OtelTracer):
    """OtelTracer 확장 - 외부 OTLP Collector로 trace export 추가"""
    
    def _initialize_tracer_provider(self, worker_id: int):
        # 부모 클래스 초기화 먼저 실행
        super()._initialize_tracer_provider(worker_id)
        
        # 추가 OTLP Exporter 설정 (Azure Monitor로 전송)
        if self._tracer_provider is not None:
            otlp_exporter = OTLPSpanExporter(
                endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True,
            )
            self._tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            print(f"[Worker {worker_id}] ✅ Added OTLP exporter → {OTEL_EXPORTER_OTLP_ENDPOINT}")


def main():
    """APO 학습 실행 - Azure Application Insights로 상세 trace 전송"""
    print(f"✅ Tracing → {OTEL_EXPORTER_OTLP_ENDPOINT}")
    print("🚀 Agent Lightning - APO Training Started")
    print("📊 Detailed traces enabled (Prompt History, Rewards, Rollouts)")
    print("=" * 50)

    # Azure OpenAI 클라이언트
    openai_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    # 초기 프롬프트 템플릿
    init_prompt = initial_prompt_template()
    init_prompt_text = init_prompt.template if hasattr(init_prompt, 'template') else str(init_prompt)
    
    print(f"\n📝 Initial Prompt ({len(init_prompt_text)} chars):")
    print("-" * 40)
    print(init_prompt_text[:500] + "..." if len(init_prompt_text) > 500 else init_prompt_text)
    print("-" * 40)

    # APO 알고리즘
    algo = agl.APO(
        openai_client,
        gradient_model=AZURE_OPENAI_DEPLOYMENT_NAME,
        apply_edit_model=AZURE_OPENAI_DEPLOYMENT_NAME,
        gradient_batch_size=4,
        beam_width=2,
        branch_factor=2,
        beam_rounds=3,
    )

    # 상세 학습 Hook (초기 프롬프트 전달)
    training_hook = DetailedTrainingHook(initial_prompt=init_prompt_text)

    # Trainer with hooks
    trainer = agl.Trainer(
        algorithm=algo,
        n_runners=4,
        tracer=OtelTracerWithExporter(),
        initial_resources={"prompt_template": init_prompt},
        adapter=agl.TraceToMessages(),
        hooks=[training_hook],  # 상세 트레이싱 Hook 추가
    )

    # 데이터셋 준비
    dataset = create_dataset()
    split_idx = int(len(dataset) * 0.8)
    train_dataset, val_dataset = dataset[:split_idx], dataset[split_idx:]

    print(f"\n📊 Dataset: {len(train_dataset)} train, {len(val_dataset)} validation")
    print(f"🤖 Model: {AZURE_OPENAI_DEPLOYMENT_NAME}")
    print("=" * 50)

    # 학습 시작
    print("\n🎓 Starting training...")
    result = trainer.fit(
        agent=quiz_agent,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
    )

    # 학습 요약 정보
    summary = training_hook.get_training_summary()
    
    # 학습 완료 후 상세 trace 전송
    tracer_inst = get_azure_tracer()
    
    # 1. 학습 완료 요약
    with tracer_inst.start_as_current_span("training.complete") as span:
        span.set_attribute("train.samples", len(train_dataset))
        span.set_attribute("val.samples", len(val_dataset))
        span.set_attribute("model", AZURE_OPENAI_DEPLOYMENT_NAME)
        span.set_attribute("training.total_rounds", summary["total_rounds"])
        span.set_attribute("training.total_rollouts", summary["total_rollouts"])
        span.set_attribute("training.prompt_versions", summary["prompt_versions"])
        span.set_attribute("training.best_reward", summary["best_reward"])
        
        # 초기 vs 최종 프롬프트 비교
        span.set_attribute("prompt.initial", summary["initial_prompt"][:2000])
        span.set_attribute("prompt.initial_length", len(summary["initial_prompt"]))
        
        if result and "prompt_template" in result:
            optimized = result["prompt_template"]
            optimized_text = optimized.template if hasattr(optimized, 'template') else str(optimized)
            span.set_attribute("prompt.final", optimized_text[:2000])
            span.set_attribute("prompt.final_length", len(optimized_text))
            span.set_attribute("prompt.changed", optimized_text != summary["initial_prompt"])
    
    # 2. 프롬프트 변화 히스토리 기록
    for i, prompt_record in enumerate(summary["prompt_history"]):
        with tracer_inst.start_as_current_span("prompt.history") as span:
            span.set_attribute("prompt.version", i + 1)
            span.set_attribute("prompt.round", prompt_record["round"])
            span.set_attribute("prompt.content", prompt_record["prompt"][:2000])
            span.set_attribute("prompt.length", len(prompt_record["prompt"]))
    
    # 3. 최종 최적화 프롬프트 (전체 내용)
    if result and "prompt_template" in result:
        optimized = result["prompt_template"]
        optimized_text = optimized.template if hasattr(optimized, 'template') else str(optimized)
        
        with tracer_inst.start_as_current_span("prompt.optimized_final") as span:
            span.set_attribute("prompt.type", "final_optimized")
            span.set_attribute("prompt.content", optimized_text[:4000])
            span.set_attribute("prompt.length", len(optimized_text))
            span.set_attribute("prompt.best_reward", summary["best_reward"])
            
            # 초기 대비 변화량
            initial_len = len(summary["initial_prompt"])
            final_len = len(optimized_text)
            span.set_attribute("prompt.length_change", final_len - initial_len)
            span.set_attribute("prompt.length_change_pct", round((final_len - initial_len) / initial_len * 100, 1) if initial_len > 0 else 0)

    # 결과 출력
    print("\n" + "=" * 50)
    print("✅ Training Complete!")
    print("=" * 50)
    print(f"📊 Total Rounds: {summary['total_rounds']}")
    print(f"📊 Total Rollouts: {summary['total_rollouts']}")
    print(f"📊 Prompt Versions: {summary['prompt_versions']}")
    print(f"🏆 Best Reward: {summary['best_reward']:.2f}")

    if result and "prompt_template" in result:
        optimized = result["prompt_template"]
        optimized_text = optimized.template if hasattr(optimized, 'template') else str(optimized)
        
        print("\n📝 Initial Prompt:")
        print("-" * 40)
        print(summary["initial_prompt"][:300] + "..." if len(summary["initial_prompt"]) > 300 else summary["initial_prompt"])
        print("-" * 40)
        
        print("\n📝 Optimized Prompt:")
        print("-" * 40)
        print(optimized_text)
        print("-" * 40)
        
        # 변화 여부 확인
        if optimized_text != summary["initial_prompt"]:
            print("✅ Prompt was optimized!")
            print(f"   Length: {len(summary['initial_prompt'])} → {len(optimized_text)} chars")
        else:
            print("⚠️ Prompt unchanged (may need more training)")

        output_path = Path(__file__).parent.parent / "app" / "optimized_prompt.txt"
        with open(output_path, "w") as f:
            f.write(optimized_text)
        print(f"\n💾 Saved to: {output_path}")

    # TracerProvider flush/shutdown (마지막 batch 유실 방지)
    shutdown_azure_tracer()

    return result


if __name__ == "__main__":
    main()
