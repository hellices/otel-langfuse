"""LLM-as-Judge 평가기"""
from pathlib import Path
import sys

from openai import AzureOpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION,
)


def create_azure_client() -> AzureOpenAI:
    """Azure OpenAI 클라이언트 생성"""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def evaluate_answer(student_answer: str, expected_answer: str, question: str) -> float:
    """
    LLM-as-Judge로 학생 답변 평가
    
    Args:
        student_answer: 학생의 답변
        expected_answer: 정답
        question: 문제
    
    Returns:
        1.0 (정답) 또는 0.0 (오답)
    """
    client = create_azure_client()
    
    eval_prompt = f"""당신은 채점자입니다. 학생 답변이 정답과 의미적으로 일치하는지 판단하세요.

문제: {question}
정답: {expected_answer}
학생 답변: {student_answer}

평가 기준:
- 표현이 달라도 의미가 같으면 정답 (예: "H₂O" = "H2O", "세종대왕" = "세종")
- 정답이 포함되어 있으면 정답 (예: 정답 "goes"에 "He goes to school"도 정답)
- 숫자는 값이 같으면 정답 (예: "15" = "15입니다" = "정답은 15")
- 언어가 달라도 의미가 같으면 정답 (예: "apple" = "애플")

1 (정답) 또는 0 (오답)만 출력하세요:"""

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": eval_prompt}],
    )
    
    result = response.choices[0].message.content.strip()
    
    # 1 또는 0 추출
    if "1" in result:
        return 1.0
    return 0.0
