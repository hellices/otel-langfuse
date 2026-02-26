"""Agent Lightning 에이전트 - APO 학습용"""
from pathlib import Path
import sys
import yaml

from openai import AzureOpenAI
import agentlightning as agl

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION,
)
from .dataset import QuizTask
from .evaluator import evaluate_answer


def load_prompts() -> dict:
    """app/prompts.yaml에서 프롬프트 로드"""
    prompts_path = Path(__file__).parent.parent / "app" / "prompts.yaml"
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise RuntimeError(f"Failed to parse YAML from '{prompts_path}': {e}") from e
    except FileNotFoundError as e:
        raise RuntimeError(f"Prompts file not found: '{prompts_path}'") from e
    except PermissionError as e:
        raise RuntimeError(f"Permission denied when reading prompts file: '{prompts_path}'") from e


def create_azure_client() -> AzureOpenAI:
    """Azure OpenAI 클라이언트 생성"""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


@agl.rollout
def quiz_agent(task: QuizTask, prompt_template: agl.PromptTemplate) -> float:
    """
    Quiz Agent - Student 프롬프트 최적화
    
    APO가 prompt_template을 최적화하여 Student가 정답을 더 잘 맞히도록 함
    
    Args:
        task: 퀴즈 태스크 (question, expected_answer, difficulty, subject)
        prompt_template: APO가 최적화하는 Student 프롬프트
    
    Returns:
        reward: 1.0 (정답) 또는 0.0 (오답)
    """
    client = create_azure_client()
    prompts = load_prompts()
    
    question = task["question"]
    expected_answer = task["expected_answer"]
    difficulty = task["difficulty"]
    
    # Student 페르소나 결정
    persona = prompts.get("student_persona", {}).get(difficulty, "학생입니다.")
    
    # Student 프롬프트 렌더링
    student_system = prompt_template.template.format(
        difficulty=difficulty,
        persona=persona,
    )
    
    # Student가 문제에 답변
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": student_system},
            {"role": "user", "content": f"문제: {question}\n\n이 문제의 정답을 말해주세요."},
        ],
    )
    
    # Content filter로 인해 None이 반환될 수 있음
    content = response.choices[0].message.content
    if content is None:
        print(f"  Q: {question[:40]}... | Expected: {expected_answer} | Got: [FILTERED] | R: 0.0")
        agl.emit_reward(0.0)
        return 0.0
    
    student_answer = content.strip()
    
    # Reward 계산 (LLM-as-Judge)
    reward = evaluate_answer(student_answer, expected_answer, question)
    
    # 디버깅 출력
    print(f"  Q: {question[:40]}... | Expected: {expected_answer} | Got: {student_answer[:30]}... | R: {reward}")
    
    # Agent Lightning에 reward emit
    agl.emit_reward(reward)
    
    return reward


def initial_prompt_template() -> agl.PromptTemplate:
    """초기 Student 프롬프트 템플릿 (APO 최적화 대상)"""
    prompts = load_prompts()
    base_prompt = prompts.get("student_answer", "문제에 답하세요.")
    
    return agl.PromptTemplate(
        template=f"""{base_prompt}

문제의 난이도: {{difficulty}}

답변 형식:
- 최종 답을 "정답은 [답]입니다" 형식으로 명확히 제시하세요
- 간결하게 답하세요""",
        engine="f-string",
    )
