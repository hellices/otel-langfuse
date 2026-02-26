"""FastAPI Chat Agent with LangGraph - Teacher-Student Quiz System"""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

from langchain_core.messages import HumanMessage

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, OTEL_EXPORTER_OTLP_ENDPOINT
from .graph import create_graph, QuizPhase

# === Globals ===
graph = None
tracer = None
session_states: dict = {}  # {session_id: {"state": ..., "last_accessed": timestamp}}

# === Constants ===
SESSION_TTL_SECONDS = 3600  # 1시간 미사용 세션 정리
RESET_KEYWORDS = ["새로", "리셋", "reset", "다시", "처음"]
NEXT_KEYWORDS = ["다음", "계속", "next", "continue", "더"]
NODE_LABELS = {
    "teacher_question": "👨‍🏫 Teacher (문제)",
    "student_answer": "🧑‍🎓 Student",
    "teacher_evaluate": "👨‍🏫 Teacher (평가)",
}


# === Models ===
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# === Helpers ===
def get_initial_state() -> dict:
    return {"phase": QuizPhase.SETUP, "difficulty": None, "subject": None, "round_count": 0}


def get_session(session_id: str) -> tuple[str, dict]:
    """세션 ID와 상태 반환 (없으면 생성), 오래된 세션 정리"""
    # 오래된 세션 정리
    now = time.time()
    expired = [k for k, v in session_states.items() if now - v.get("last_accessed", 0) > SESSION_TTL_SECONDS]
    for k in expired:
        del session_states[k]

    sid = session_id or str(uuid4())
    if sid not in session_states:
        session_states[sid] = {**get_initial_state(), "last_accessed": now}
    else:
        session_states[sid]["last_accessed"] = now
    return sid, session_states[sid]


def process_commands(user_input: str, state: dict) -> str:
    """리셋/다음 명령 처리 후 phase 반환"""
    phase = state.get("phase", QuizPhase.SETUP)
    lower_input = user_input.lower()
    
    if any(kw in lower_input for kw in RESET_KEYWORDS):
        state.update(get_initial_state())
        return QuizPhase.SETUP
    
    if phase == QuizPhase.COMPLETE and any(kw in lower_input for kw in NEXT_KEYWORDS):
        state["phase"] = QuizPhase.QUESTIONING
        return QuizPhase.QUESTIONING
    
    return phase


def build_invoke_state(user_input: str, phase: str, state: dict) -> dict:
    return {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "phase": phase,
        "difficulty": state.get("difficulty"),
        "subject": state.get("subject"),
        "round_count": state.get("round_count", 0),
    }


def update_session_from_result(session_id: str, result: dict):
    session_states[session_id] = {
        "phase": result.get("phase", QuizPhase.SETUP),
        "difficulty": result.get("difficulty"),
        "subject": result.get("subject"),
        "round_count": result.get("round_count", 0),
    }


def extract_responses(result: dict) -> str:
    responses = [
        msg.content for msg in result.get("messages", [])
        if hasattr(msg, "content") and msg.content and not isinstance(msg, HumanMessage)
    ]
    return "\n\n".join(responses) if responses else "응답을 생성할 수 없습니다."


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# === OpenTelemetry Setup ===
def setup_opentelemetry():
    global tracer
    os.environ.setdefault("OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT", "65535")
    
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "teacher-student-quiz"}))
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    ))
    trace.set_tracer_provider(provider)
    LangchainInstrumentor().instrument()
    tracer = trace.get_tracer(__name__)
    
    print(f"✅ OpenTelemetry → {OTEL_EXPORTER_OTLP_ENDPOINT}")
    return tracer


# === App Lifecycle ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, tracer
    tracer = setup_opentelemetry()
    graph = create_graph()
    print(f"✅ LangGraph initialized: {AZURE_OPENAI_DEPLOYMENT_NAME}")
    yield
    print("Shutting down...")


# === FastAPI App ===
app = FastAPI(title="Teacher-Student Quiz", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "static"), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# === Routes ===
@app.get("/", response_class=HTMLResponse)
async def root():
    return (Path(__file__).parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
async def health():
    return {"status": "healthy", "graph_initialized": graph is not None}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not graph:
        raise HTTPException(503, "Agent not initialized")
    
    session_id, state = get_session(request.session_id)
    user_input = request.message.strip()
    phase = process_commands(user_input, state)
    
    config = {"configurable": {"thread_id": session_id}}
    invoke_state = build_invoke_state(user_input, phase, state)
    
    result = graph.invoke(invoke_state, config=config)
    update_session_from_result(session_id, result)
    
    return ChatResponse(response=extract_responses(result), session_id=session_id)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not graph:
        raise HTTPException(503, "Agent not initialized")
    
    async def generate() -> AsyncGenerator[str, None]:
        session_id, state = get_session(request.session_id)
        user_input = request.message.strip()
        phase = process_commands(user_input, state)
        
        yield sse_event({"type": "session", "session_id": session_id})
        
        config = {"configurable": {"thread_id": session_id}}
        invoke_state = build_invoke_state(user_input, phase, state)
        
        with tracer.start_as_current_span("chat_stream") as span:
            span.set_attribute("langfuse.trace.name", "langgraph-session")
            span.set_attribute("langfuse.session.id", session_id)
            span.set_attribute("langfuse.trace.input", user_input)
            
            final_output = ""
            try:
                async for event in graph.astream(invoke_state, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if not isinstance(node_output, dict) or "messages" not in node_output:
                            continue
                        
                        for msg in node_output["messages"]:
                            if not (hasattr(msg, "content") and msg.content):
                                continue
                            
                            content = msg.content
                            final_output = content
                            
                            # 노드 라벨
                            label = NODE_LABELS.get(node_name, node_name)
                            if node_name == "teacher_question":
                                state["round_count"] = state.get("round_count", 0) + 1
                                label = f"👨‍🏫 Teacher (문제 #{state['round_count']})"
                            
                            # SSE 이벤트 전송
                            if node_name in NODE_LABELS:
                                yield sse_event({"type": "node_start", "node": node_name, "label": label})
                            
                            yield sse_event({"type": "message", "node": node_name, "content": content})
                            
                            if node_name in NODE_LABELS:
                                yield sse_event({"type": "node_end", "node": node_name})
                            
                            # 대기 메시지
                            waiting_msgs = {
                                "teacher_question": "🧑‍🎓 Student가 생각 중...",
                                "student_answer": "👨‍🏫 Teacher가 평가 중...",
                            }
                            if node_name in waiting_msgs:
                                yield sse_event({"type": "waiting", "message": waiting_msgs[node_name]})
                            
                            await asyncio.sleep(0.1)
            except Exception as e:
                yield sse_event({"type": "error", "message": str(e)})
            
            if final_output:
                span.set_attribute("langfuse.trace.output", final_output[:10000])
        
        # 최종 상태 저장
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            update_session_from_result(session_id, final_state.values)
        
        yield sse_event({"type": "done"})
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
