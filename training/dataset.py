"""학습 데이터셋 정의"""
from typing import TypedDict


class QuizTask(TypedDict):
    """퀴즈 태스크 정의"""
    question: str        # 출제할 문제
    expected_answer: str # 정답
    difficulty: str      # 난이도 (쉬움, 보통, 어려움)
    subject: str         # 과목


def create_dataset() -> list[QuizTask]:
    """학습 데이터셋 - LLM이 자주 틀리는 함정 문제 (안전한 버전)"""
    return [
        # === 기준선 (쉬움) ===
        {"question": "5 + 10은?", "expected_answer": "15", "difficulty": "쉬움", "subject": "수학"},
        {"question": "물의 화학식은?", "expected_answer": "H2O", "difficulty": "쉬움", "subject": "과학"},
        
        # === 수학 함정 ===
        {
            "question": "1달러짜리 공과 방망이의 총 가격은 1.10달러입니다. 방망이가 공보다 1달러 더 비쌉니다. 공의 가격은 몇 달러인가요?",
            "expected_answer": "0.05",
            "difficulty": "함정",
            "subject": "수학"
        },
        {
            "question": "30을 2로 나누고 10을 더하면?",
            "expected_answer": "25",
            "difficulty": "함정",
            "subject": "수학"
        },
        {
            "question": "8을 반으로 나누면?",
            "expected_answer": "4",
            "difficulty": "함정",
            "subject": "수학"
        },
        
        # === 언어/논리 함정 ===
        {
            "question": "철수의 아버지에게는 아들이 셋 있습니다. 첫째는 '월요일', 둘째는 '화요일'입니다. 셋째의 이름은?",
            "expected_answer": "철수",
            "difficulty": "함정",
            "subject": "언어"
        },
        {
            "question": "에밀리의 어머니에게는 딸이 4명 있습니다: 봄, 여름, 가을. 넷째 딸의 이름은?",
            "expected_answer": "에밀리",
            "difficulty": "함정",
            "subject": "언어"
        },
        {
            "question": "1월과 2월 중에서 28일이 있는 달은 몇 개인가요?",
            "expected_answer": "2",
            "difficulty": "함정",
            "subject": "논리"
        },
        
        # === 패턴 인식 함정 ===
        {
            "question": "버스 기사가 출발할 때 승객 10명이 있었습니다. 첫 정류장에서 3명이 내리고 5명이 탔습니다. 버스 기사의 나이는 몇 살인가요?",
            "expected_answer": "알 수 없다",
            "difficulty": "함정",
            "subject": "논리"
        },
        {
            "question": "릴리 패드가 연못을 덮는 데 48일이 걸립니다. 매일 2배로 자랍니다. 연못의 절반을 덮는 데 며칠이 걸리나요?",
            "expected_answer": "47",
            "difficulty": "함정",
            "subject": "논리"
        },
        
        # === 상식 역이용 ===
        {
            "question": "모세가 방주에 각 동물을 몇 쌍씩 태웠나요?",
            "expected_answer": "0",
            "difficulty": "함정",
            "subject": "상식"
        },
        {
            "question": "피자 한 판을 8조각으로 자르려면 최소 몇 번 칼질해야 하나요?",
            "expected_answer": "4",
            "difficulty": "함정",
            "subject": "논리"
        },
        
        # === 계산 함정 ===
        {
            "question": "사과 5개가 있습니다. 2개를 가져가면 몇 개를 갖게 되나요?",
            "expected_answer": "2",
            "difficulty": "함정",
            "subject": "논리"
        },
        {
            "question": "시계가 3시를 칠 때 3초가 걸립니다. 6시를 치는 데 몇 초가 걸리나요?",
            "expected_answer": "5",
            "difficulty": "함정",
            "subject": "논리"
        },
    ]
