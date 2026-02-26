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
    LLM-as-Judge로 학생 답변 평가 (엄격 모드)
    
    Args:
        student_answer: 학생의 답변
        expected_answer: 정답
        question: 문제
    
    Returns:
        1.0 (정답) 또는 0.0 (오답)
    """
    client = create_azure_client()
    
    eval_prompt = f"""당신은 매우 엄격한 채점자입니다. 학생의 최종 답변만 평가합니다.

문제: {question}
정답: {expected_answer}
학생 답변: {student_answer}

엄격한 평가 기준:
1. 학생이 제시한 "최종 숫자/값"만 정답과 비교하세요.
2. 풀이 과정이 맞아도 최종 답이 틀리면 0점입니다.
3. 정답과 정확히 일치하는 값이 최종 답변에 없으면 0점입니다.
4. "알 수 없다", "정보 부족" 등의 답변은 정답이 그것일 때만 1점입니다.

예시:
- 정답 "0", 학생 "방주는 노아가 만들었으므로 모세는 0쌍을 태웠습니다" → 최종값 0 → 1점
- 정답 "0", 학생 "노아가 7쌍씩 태웠습니다" → 최종값 7 → 0점  
- 정답 "47", 학생 "절반은 24일" → 최종값 24 → 0점
- 정답 "철수", 학생 "셋째는 삼월입니다" → 최종값 삼월 → 0점
- 정답 "2", 학생 "2개 가져가면 3개 남습니다" → 최종값 3 → 0점 (남은 개수가 아니라 가져간 개수를 물었음)

학생의 최종 답변 값이 정답 "{expected_answer}"와 정확히 일치하면 1, 아니면 0을 출력하세요:"""

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": eval_prompt}],
    )
    
    content = response.choices[0].message.content
    if content is None:
        return 0.0
    
    result = content.strip()
    
    # 정확히 "1"인 경우만 정답 ("10", "1.0" 등 오탐 방지)
    if result == "1":
        return 1.0
    return 0.0
