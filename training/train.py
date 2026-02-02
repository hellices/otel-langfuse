"""Agent Lightning RL 학습 스크립트 - APO (Automatic Prompt Optimization)"""
import os
from pathlib import Path
import sys

# AgentOps 비활성화 (OtelTracer 사용)
os.environ.setdefault("AGENTOPS_API_KEY", "")
os.environ.setdefault("AGENTOPS_LOGGING_LEVEL", "CRITICAL")

from openai import AsyncAzureOpenAI
import agentlightning as agl

from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

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

from .agent import quiz_agent, initial_prompt_template
from .dataset import create_dataset


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
    """APO 학습 실행"""
    print(f"✅ Tracing → {OTEL_EXPORTER_OTLP_ENDPOINT}")
    print("🚀 Agent Lightning - APO Training Started")
    print("=" * 50)

    # Azure OpenAI 클라이언트
    openai_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )

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

    # Trainer
    trainer = agl.Trainer(
        algorithm=algo,
        n_runners=4,
        tracer=OtelTracerWithExporter(),
        initial_resources={"prompt_template": initial_prompt_template()},
        adapter=agl.TraceToMessages(),
    )

    # 데이터셋 준비
    dataset = create_dataset()
    split_idx = int(len(dataset) * 0.8)
    train_dataset, val_dataset = dataset[:split_idx], dataset[split_idx:]

    print(f"📊 Dataset: {len(train_dataset)} train, {len(val_dataset)} validation")
    print(f"🤖 Model: {AZURE_OPENAI_DEPLOYMENT_NAME}")
    print("=" * 50)

    # 학습 시작
    print("\n🎓 Starting training...")
    result = trainer.fit(
        agent=quiz_agent,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
    )

    # 결과 출력
    print("\n" + "=" * 50)
    print("✅ Training Complete!")
    print("=" * 50)

    if result and "prompt_template" in result:
        optimized = result["prompt_template"]
        print("\n📝 Optimized Student Prompt:")
        print("-" * 40)
        print(optimized.template)
        print("-" * 40)

        output_path = Path(__file__).parent.parent / "app" / "optimized_prompt.txt"
        with open(output_path, "w") as f:
            f.write(optimized.template)
        print(f"💾 Saved to: {output_path}")

    return result


if __name__ == "__main__":
    main()
