"""학습 데이터셋 정의"""
from typing import TypedDict


class QuizTask(TypedDict):
    """퀴즈 태스크 정의"""
    question: str        # 출제할 문제
    expected_answer: str # 정답
    difficulty: str      # 난이도 (쉬움, 보통, 어려움)
    subject: str         # 과목


def create_dataset() -> list[QuizTask]:
    """학습 데이터셋 - 다양한 난이도의 문제와 정답 쌍"""
    return [
        # === 수학 (쉬움) ===
        {"question": "5 + 10은 얼마인가요?", "expected_answer": "15", "difficulty": "쉬움", "subject": "수학"},
        {"question": "3 × 4는 얼마인가요?", "expected_answer": "12", "difficulty": "쉬움", "subject": "수학"},
        {"question": "20 - 8은 얼마인가요?", "expected_answer": "12", "difficulty": "쉬움", "subject": "수학"},
        
        # === 수학 (보통) ===
        {"question": "2x + 4 = 14일 때, x의 값은?", "expected_answer": "5", "difficulty": "보통", "subject": "수학"},
        {"question": "36의 제곱근은?", "expected_answer": "6", "difficulty": "보통", "subject": "수학"},
        {"question": "200의 15%는?", "expected_answer": "30", "difficulty": "보통", "subject": "수학"},
        {"question": "3:4 = x:20일 때, x는?", "expected_answer": "15", "difficulty": "보통", "subject": "수학"},
        {"question": "연속하는 세 자연수의 합이 24일 때, 가장 큰 수는?", "expected_answer": "9", "difficulty": "보통", "subject": "수학"},
        
        # === 수학 (어려움) ===
        {"question": "x^2 - 5x + 6 = 0의 두 근의 합은?", "expected_answer": "5", "difficulty": "어려움", "subject": "수학"},
        {"question": "log10(1000)의 값은?", "expected_answer": "3", "difficulty": "어려움", "subject": "수학"},
        {"question": "1부터 100까지 자연수의 합은?", "expected_answer": "5050", "difficulty": "어려움", "subject": "수학"},
        
        # === 과학 (쉬움) ===
        {"question": "물의 화학식은?", "expected_answer": "H2O", "difficulty": "쉬움", "subject": "과학"},
        {"question": "지구에서 가장 가까운 별은?", "expected_answer": "태양", "difficulty": "쉬움", "subject": "과학"},
        
        # === 과학 (보통) ===
        {"question": "빛의 속도는 초당 약 몇 km인가요?", "expected_answer": "300000", "difficulty": "보통", "subject": "과학"},
        {"question": "원자번호 1번인 원소는?", "expected_answer": "수소", "difficulty": "보통", "subject": "과학"},
        {"question": "DNA의 이중나선 구조를 발견한 과학자 2명 중 한 명은?", "expected_answer": "왓슨", "difficulty": "보통", "subject": "과학"},
        
        # === 역사 ===
        {"question": "한글을 창제한 왕은?", "expected_answer": "세종대왕", "difficulty": "쉬움", "subject": "역사"},
        {"question": "임진왜란이 발발한 연도는?", "expected_answer": "1592", "difficulty": "보통", "subject": "역사"},
        {"question": "조선 왕조의 마지막 왕은?", "expected_answer": "순종", "difficulty": "보통", "subject": "역사"},
        
        # === 영어 (쉬움) ===
        {"question": "'사과'를 영어로?", "expected_answer": "apple", "difficulty": "쉬움", "subject": "영어"},
        {"question": "'학교'를 영어로?", "expected_answer": "school", "difficulty": "쉬움", "subject": "영어"},
        
        # === 영어 (보통) ===
        {"question": "'He go to school every day'에서 틀린 부분을 고치면?", "expected_answer": "goes", "difficulty": "보통", "subject": "영어"},
        {"question": "'빠른'의 비교급은?", "expected_answer": "faster", "difficulty": "보통", "subject": "영어"},
        
        # === 일반상식 ===
        {"question": "1년은 몇 개월?", "expected_answer": "12", "difficulty": "쉬움", "subject": "일반상식"},
        {"question": "세계에서 가장 긴 강은?", "expected_answer": "나일강", "difficulty": "보통", "subject": "일반상식"},
        {"question": "올림픽은 몇 년마다 열리나요?", "expected_answer": "4", "difficulty": "쉬움", "subject": "일반상식"},
        {"question": "세계에서 가장 높은 산은?", "expected_answer": "에베레스트", "difficulty": "쉬움", "subject": "일반상식"},
    ]
