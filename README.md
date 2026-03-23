# ⛳ 스크린골프 대전 관리 프로그램

## 📦 설치 방법

### 1단계: Python 설치 확인
```bash
python --version   # Python 3.9 이상 권장
```
→ 없으면 https://www.python.org/downloads/ 에서 설치

### 2단계: 가상 환경 생성 (선택, 권장)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3단계: 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 4단계: 앱 실행
```bash
streamlit run screen_golf_app.py
```
→ 브라우저에서 자동으로 http://localhost:8501 이 열립니다.

---

## 📁 파일 구조
```
screen_golf_app.py   ← 메인 앱
requirements.txt     ← 필요 라이브러리
golf_data/           ← 자동 생성되는 데이터 폴더
  ├── games.json     ← 경기 결과 저장
  └── members.csv    ← 회원 목록 저장
```

## 🎯 주요 기능
| 메뉴 | 설명 |
|------|------|
| 🏠 홈 | 전체 현황 요약 |
| ➕ 경기 입력 | 날짜/장소/참가자/타수 입력, 팀 배정 |
| 📋 경기 목록 | 과거 경기 조회 및 삭제 |
| 📊 통계 대시보드 | 개인/팀 승률·타수 시각화 |
| 👤 회원 관리 | 회원 추가·수정·삭제 |

## 📌 계산 방식
- **개인전**: `최종타수 - G핸디` → 낮은 순서대로 순위 산정
- **팀전**: `팀원 타수 합 - 팀원 핸디 합` → 낮은 팀 승리
