import os
import openai
import mysql.connector
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

# db설정
db = mysql.connector.connect(
    # host = os.getenv("DB_HOST"),
    # user = os.getenv("DB_USER"),
    # password = os.getenv("DB_PASSWORD"),
    user="root",
    password="n9800211",
    database="legacy",
)
cursor = db.cursor(dictionary=True)

QUIZ_PROMPT = """
너는 한국어 역사 퀴즈 제작자야.
주어진 유적지 이름을 보고, 그 유적지와 관련된 퀴즈 10개를 만들어.
퀴즈 형식은 JSON 배열이고, 각 항목은 다음과 같아야 해:

[
  {
    "quizProblem": "문제",
    "answerOption": "정답",
    "hint": "힌트",
    "optionValues": ["보기1", "보기2", "보기3", "보기4", "보기5"]
  }
]

반드시 유효한 JSON 형식으로만 답변해.
```json이나 다른 마크다운 문법은 사용하지 마.
"""


def check_tables():
    try:
        cursor.execute("DESCRIBE quiz")
        quiz_columns = [row['Field'] for row in cursor.fetchall()]
        print(f"Quiz 테이블 컬럼: {quiz_columns}")

        cursor.execute("DESCRIBE quiz_option")
        option_columns = [row['Field'] for row in cursor.fetchall()]
        print(f"Quiz_option 테이블 컬럼: {option_columns}")

        return quiz_columns, option_columns
    except Exception as e:
        print(f"테이블 구조 확인 오류: {e}")
        return [], []


def generate_quizzes(ruins_name):
    """GPT를 이용해 해당 유적지 퀴즈 10개 생성"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": QUIZ_PROMPT},
                {"role": "user", "content": f"유적지 이름: {ruins_name}"}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        quizzes = json.loads(content)

        if not isinstance(quizzes, list):
            print(f"응답이 배열이 아님: {ruins_name}")
            return []

        valid_quizzes = []
        for q in quizzes:
            if all(key in q for key in ["quizProblem", "answerOption", "hint", "optionValues"]):
                if isinstance(q["optionValues"], list) and len(q["optionValues"]) >= 2:
                    valid_quizzes.append(q)
                else:
                    print(f"보기가 부족한 문제 건너뜀: {q.get('quizProblem', 'Unknown')}")
            else:
                print(f"필수 필드가 없는 문제 건너뜀: {q}")

        return valid_quizzes

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {ruins_name} - {e}")
        print(f"응답 내용: {content}")
        return []
    except Exception as e:
        print(f"퀴즈 생성 오류: {ruins_name} - {e}")
        return []


def save_quizzes(ruins_id, quizzes):
    try:
        for q in quizzes:
            cursor.execute(
                """
                INSERT INTO quiz (ruins_id, quiz_problem, answer_option, hint)
                VALUES (%s, %s, %s, %s)
                """,
                (ruins_id, q["quizProblem"], q["answerOption"], q["hint"])
            )
            quiz_id = cursor.lastrowid

            for opt in q["optionValues"]:
                cursor.execute(
                    """
                    INSERT INTO quiz_option (quiz_id, option_value)
                    VALUES (%s, %s)
                    """,
                    (quiz_id, opt)
                )

        db.commit()
        return True
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        db.rollback()
        return False


def main():
    if not openai.api_key:
        print("OpenAI API 키가 설정되지 않았습니다!")
        print("환경변수 OPENAI_API_KEY를 설정하거나 코드에서 직접 설정하세요.")
        return

    print("테이블 구조 확인 중")
    quiz_columns, option_columns = check_tables()

    if not quiz_columns or not option_columns:
        print("테이블 구조 확인 실패!")
        return

    try:
        cursor.execute("SELECT ruins_id, name FROM ruins")
        ruins_list = cursor.fetchall()

        if not ruins_list:
            print("유적지 데이터가 없습니다!")
            return

        print(f"총 {len(ruins_list)}개의 유적지를 처리합니다.")

    except Exception as e:
        print(f"유적지 데이터 조회 실패: {e}")
        return

    success_count = 0
    for i, ruins in enumerate(ruins_list, 1):
        ruins_id = ruins["ruins_id"]
        name = ruins["name"]

        print(f"[{i}/{len(ruins_list)}] {name} 퀴즈 생성 중...")

        quizzes = generate_quizzes(name)
        if quizzes:
            if save_quizzes(ruins_id, quizzes):
                print(f"{name} 퀴즈 {len(quizzes)}개 저장 완료")
                success_count += 1
            else:
                print(f"{name} 퀴즈 저장 실패")
        else:
            print(f"{name} 퀴즈 생성 실패")

    print(f"\n 작업 완료: {success_count}/{len(ruins_list)}개 유적지 처리 성공")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
    finally:
        if 'cursor' in globals():
            cursor.close()
        if 'db' in globals():
            db.close()
        print(" 데이터베이스 연결 종료")