"""
⛳ 스크린골프 결과 관리 프로그램
Screen Golf Result Management System
"""

import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import date
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai

# ──────────────────────────────────────────
# 설정 & 상수
# ──────────────────────────────────────────
DATA_DIR = "golf_data"
GAMES_FILE = os.path.join(DATA_DIR, "games.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
PLAYERS_FILE = os.path.join(DATA_DIR, "players.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ──────────────────────────────────────────
# 암호 보호
# ──────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 🔒 스크린골프 성적 관리")
    pw = st.text_input("암호를 입력하세요", type="password", key="pw_input")
    if st.button("확인"):
        if pw == st.secrets.get("password", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("암호가 틀렸습니다.")
    return False

if not check_password():
    st.stop()


# ──────────────────────────────────────────
# 데이터 로드 / 저장 헬퍼
# ──────────────────────────────────────────
def load_json(path: str) -> list:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_games_df() -> pd.DataFrame:
    data = load_json(GAMES_FILE)
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_results_df() -> pd.DataFrame:
    data = load_json(RESULTS_FILE)
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_players_roster() -> list:
    """등록된 선수 명단 로드"""
    return load_json(PLAYERS_FILE)


def save_players_roster(players: list):
    save_json(PLAYERS_FILE, players)


def analyze_golf_screenshot(image_bytes: bytes, media_type: str) -> list:
    """Gemini Vision으로 스크린골프 결과 스크린샷 분석 → [{name, score}] 반환"""
    api_key = st.secrets.get("GOOGLE_AI_API_KEY", "")
    if not api_key:
        st.error("⚠️ Streamlit Secrets에 GOOGLE_AI_API_KEY를 설정해주세요.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    import PIL.Image
    import io
    image = PIL.Image.open(io.BytesIO(image_bytes))

    prompt = (
        "이 스크린골프 결과 이미지에서 각 선수의 정보를 추출해주세요.\n\n"
        "각 선수 카드에서:\n"
        "- name: 닉네임/이름 (상단에 표시된 텍스트)\n"
        "- score: 최종 타수 (가장 크게 표시된 숫자, 괄호 안 +/- 숫자 제외)\n\n"
        "JSON 배열 형식으로만 답변하세요 (다른 설명 없이):\n"
        '[{"name": "선수이름", "score": 숫자}, ...]'
    )

    response = model.generate_content([prompt, image])
    raw = response.text.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ──────────────────────────────────────────
# 핵심 계산 로직
# ──────────────────────────────────────────
def calc_individual_ranking(players: list) -> pd.DataFrame:
    """개인전 순위: 최종 타수 - G핸디 오름차순"""
    df = pd.DataFrame(players)
    df["net_score"] = df["score"] - df["handicap"]
    df = df.sort_values("net_score").reset_index(drop=True)
    df.index += 1
    df.index.name = "순위"
    return df


def calc_team_ranking(players: list) -> pd.DataFrame:
    """팀전 순위: 팀별 (타수 합 - 핸디 합) 낮은 팀 승"""
    df = pd.DataFrame(players)
    team_summary = (
        df.groupby("team")
        .agg(
            total_score=("score", "sum"),
            total_handicap=("handicap", "sum"),
            members=("name", list),
        )
        .reset_index()
    )
    team_summary["net_score"] = (
        team_summary["total_score"] - team_summary["total_handicap"]
    )
    team_summary = team_summary.sort_values("net_score").reset_index(drop=True)
    return team_summary


# ──────────────────────────────────────────
# Streamlit 페이지 설정
# ──────────────────────────────────────────
st.set_page_config(
    page_title="⛳ 스크린골프 대전",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
# 커스텀 CSS
# ──────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    min-height: 100vh;
}

[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05) !important;
    border-right: 1px solid rgba(255,255,255,0.1);
}

.golf-card {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    backdrop-filter: blur(10px);
}

.main-title {
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(90deg, #56CCF2, #2F80ED, #9B51E0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    margin-bottom: 4px;
    letter-spacing: -1px;
}
.sub-title {
    text-align: center;
    color: rgba(255,255,255,0.55);
    font-size: 0.95rem;
    margin-bottom: 32px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.section-header {
    font-size: 1.2rem;
    font-weight: 700;
    color: #56CCF2;
    border-left: 4px solid #2F80ED;
    padding-left: 12px;
    margin: 20px 0 14px;
}

.win-banner {
    background: linear-gradient(135deg, #F2994A, #F2C94C);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    color: #1a1a1a;
    font-weight: 900;
    font-size: 1.4rem;
    margin: 16px 0;
}

.stat-box {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 18px;
    text-align: center;
}
.stat-number {
    font-size: 2rem;
    font-weight: 900;
    color: #56CCF2;
}
.stat-label {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.5);
    margin-top: 4px;
}

div.stButton > button {
    background: linear-gradient(135deg, #2F80ED, #9B51E0);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1rem;
    padding: 10px 28px;
    transition: all 0.3s ease;
}
div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(47,128,237,0.5);
}

.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.6) !important;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    color: #56CCF2 !important;
    border-bottom-color: #56CCF2 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────
def init_session():
    defaults = {
        "players": [],
        "game_mode": "개인전",
        "current_game_id": None,
        "result_saved": False,
        "screenshot_players": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()

# ──────────────────────────────────────────
# 사이드바 네비게이션
# ──────────────────────────────────────────
APP_VERSION = "v1.0.0"

with st.sidebar:
    st.markdown(f"## ⛳ 스크린골프 결과")
    st.caption(APP_VERSION)
    st.markdown("---")
    menu = st.radio(
        "메뉴",
        ["🏌️ 경기 입력", "📊 결과 확인", "📈 누적 통계", "📋 전체 경기 기록", "👥 선수 관리"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    games_df = get_games_df()
    results_df = get_results_df()
    total_games = len(games_df) if not games_df.empty else 0
    total_players = (
        results_df["name"].nunique()
        if not results_df.empty and "name" in results_df.columns
        else 0
    )
    st.markdown(
        f"""
        <div class="stat-box">
            <div class="stat-number">{total_games}</div>
            <div class="stat-label">총 경기 수</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="stat-box">
            <div class="stat-number">{total_players}</div>
            <div class="stat-label">등록 선수</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════
# 1. 경기 입력
# ══════════════════════════════════════════
if "경기 입력" in menu:
    st.markdown('<div class="main-title">⛳ 스크린골프 결과</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Screen Golf Result Manager</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["① 경기 정보", "② 참가자 등록", "③ 타수 입력 & 저장"])

    # ── 탭1: 경기 기본 정보
    with tab1:
        st.markdown('<div class="section-header">경기 기본 정보</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            game_date = st.date_input("📅 날짜", value=date.today())
            venue = st.text_input("🏢 장소", placeholder="예: 골프존 강남점")
        with col2:
            field_name = st.text_input("🌿 필드명", placeholder="예: 파인밸리 (18홀)")
            game_mode = st.selectbox("🎯 경기 방식", ["개인전", "팀전"])
            st.session_state["game_mode"] = game_mode

        if st.button("경기 정보 저장 ✅", use_container_width=True):
            if not venue or not field_name:
                st.error("장소와 필드명을 입력해주세요!")
            else:
                import uuid
                game_id = str(uuid.uuid4())[:8]
                st.session_state["current_game_id"] = game_id
                st.session_state["current_game_meta"] = {
                    "game_id": game_id,
                    "date": str(game_date),
                    "venue": venue,
                    "field": field_name,
                    "mode": game_mode,
                }
                st.success(f"✅ 경기 정보 저장 완료! (ID: {game_id})")

        if "current_game_meta" in st.session_state:
            meta = st.session_state["current_game_meta"]
            st.markdown(
                f"""
                <div class="golf-card" style="margin-top:20px;">
                    <b style="color:#56CCF2;">현재 설정된 경기 정보</b><br><br>
                    📅 {meta['date']} &nbsp;&nbsp; 🏢 {meta['venue']} &nbsp;&nbsp;
                    🌿 {meta['field']} &nbsp;&nbsp; 🎯 {meta['mode']}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 탭2: 참가자 등록
    with tab2:
        st.markdown('<div class="section-header">참가자 등록</div>', unsafe_allow_html=True)

        # 📸 스크린샷 자동 입력
        with st.expander("📸 스크린샷에서 자동 입력", expanded=False):
            uploaded_img = st.file_uploader(
                "스크린골프 결과 스크린샷을 업로드하세요",
                type=["jpg", "jpeg", "png", "webp"],
                key="screenshot_uploader",
            )
            if uploaded_img is not None:
                st.image(uploaded_img, width=300)
                if st.button("🔍 선수 정보 자동 추출", use_container_width=True):
                    with st.spinner("Claude가 스크린샷을 분석 중입니다..."):
                        img_bytes = uploaded_img.read()
                        ext = uploaded_img.type  # e.g. "image/jpeg"
                        try:
                            extracted = analyze_golf_screenshot(img_bytes, ext)
                            if extracted:
                                st.session_state["screenshot_players"] = extracted
                                st.success(f"✅ {len(extracted)}명의 선수 정보를 추출했습니다!")
                            else:
                                st.warning("선수 정보를 추출하지 못했습니다.")
                        except Exception as e:
                            st.error(f"분석 오류: {e}")

            if st.session_state.get("screenshot_players"):
                extracted = st.session_state["screenshot_players"]
                st.markdown("**추출된 선수 목록 (핸디 확인 후 추가)**")
                for ep in extracted:
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.write(f"**{ep['name']}**  타수: {ep['score']}")
                    with c2:
                        ep_handi = st.number_input(
                            "G핸디", min_value=-30.0, max_value=50.0, value=0.0,
                            step=0.1, format="%.1f",
                            key=f"ep_handi_{ep['name']}",
                            label_visibility="collapsed",
                        )
                    with c3:
                        if st.button("추가", key=f"ep_add_{ep['name']}"):
                            name = ep["name"]
                            if any(p["name"] == name for p in st.session_state["players"]):
                                st.warning(f"{name} 이미 등록됨")
                            else:
                                team = None
                                if st.session_state["game_mode"] == "팀전":
                                    team = "A팀"
                                st.session_state["players"].append({
                                    "name": name,
                                    "handicap": ep_handi,
                                    "score": int(ep["score"]),
                                    "team": team,
                                })
                                st.success(f"✅ {name} 추가!")
                                st.rerun()
                if st.button("📋 전체 추가 (핸디 0으로)", use_container_width=True):
                    added = 0
                    for ep in extracted:
                        if not any(p["name"] == ep["name"] for p in st.session_state["players"]):
                            st.session_state["players"].append({
                                "name": ep["name"],
                                "handicap": 0.0,
                                "score": int(ep["score"]),
                                "team": None,
                            })
                            added += 1
                    if added:
                        st.success(f"✅ {added}명 추가 완료! (핸디는 아래에서 수정하세요)")
                        st.session_state["screenshot_players"] = []
                        st.rerun()

        st.markdown("---")
        roster = get_players_roster()
        roster_names = [p["name"] for p in roster]

        # 선수 명단에서 불러오기
        if roster:
            st.markdown("**📋 등록된 선수 명단에서 선택**")
            col_sel, col_sel_btn = st.columns([3, 1])
            with col_sel:
                selected_from_roster = st.selectbox(
                    "선수 선택",
                    ["(직접 입력)"] + roster_names,
                    key="roster_select",
                    label_visibility="collapsed",
                )
            with col_sel_btn:
                if st.button("불러오기 ⬇️", use_container_width=True, key="load_from_roster"):
                    if selected_from_roster != "(직접 입력)":
                        matched = next((p for p in roster if p["name"] == selected_from_roster), None)
                        if matched:
                            st.session_state["prefill_name"] = matched["name"]
                            st.session_state["prefill_handi"] = matched["handicap"]
                            st.rerun()
            st.markdown("---")

        # 이름/핸디 입력 (불러오기로 미리 채워질 수 있음)
        prefill_name = st.session_state.pop("prefill_name", "")
        prefill_handi = st.session_state.pop("prefill_handi", 0.0)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_name = st.text_input("👤 이름", value=prefill_name, key="new_name_input")
        with col2:
            new_handicap = st.number_input(
                "🎯 G핸디", min_value=-30.0, max_value=50.0, value=float(prefill_handi), step=0.1, format="%.1f", key="new_handi_input"
            )
        with col3:
            if st.session_state["game_mode"] == "팀전":
                new_team = st.selectbox("팀", ["A팀", "B팀", "C팀", "D팀"], key="new_team_input")
            else:
                new_team = None
                st.write("(개인전)")

        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button("➕ 참가자 추가", use_container_width=True):
                if not new_name.strip():
                    st.error("이름을 입력해주세요!")
                elif any(p["name"] == new_name.strip() for p in st.session_state["players"]):
                    st.error("이미 등록된 참가자입니다!")
                else:
                    st.session_state["players"].append(
                        {
                            "name": new_name.strip(),
                            "handicap": new_handicap,
                            "score": 72,
                            "team": new_team,
                        }
                    )
                    st.success(f"✅ {new_name.strip()} 등록 완료!")
                    st.rerun()

        with col_clear:
            if st.button("🗑️ 전체 초기화", use_container_width=True):
                st.session_state["players"] = []
                st.rerun()

        # 삭제 기능 포함 참가자 목록
        if st.session_state["players"]:
            st.markdown('<div class="section-header">현재 참가자 목록</div>', unsafe_allow_html=True)
            for i, p in enumerate(st.session_state["players"]):
                c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
                with c1:
                    st.write(f"**{p['name']}**")
                with c2:
                    st.write(f"핸디: {p['handicap']}")
                with c3:
                    if p.get("team"):
                        st.write(f"팀: {p['team']}")
                with c4:
                    st.write("")
                with c5:
                    if st.button("❌", key=f"del_{i}"):
                        st.session_state["players"].pop(i)
                        st.rerun()

            # 팀전: 팀 구성 요약
            if st.session_state["game_mode"] == "팀전":
                st.markdown('<div class="section-header">팀 구성 현황</div>', unsafe_allow_html=True)
                team_groups = {}
                for p in st.session_state["players"]:
                    t = p["team"] or "미배정"
                    team_groups.setdefault(t, []).append(f"{p['name']} (핸디:{p['handicap']})")

                team_colors = {
                    "A팀": "#2F80ED", "B팀": "#EB5757",
                    "C팀": "#27AE60", "D팀": "#9B51E0", "미배정": "#888",
                }
                cols = st.columns(max(len(team_groups), 1))
                for col, (team, members) in zip(cols, team_groups.items()):
                    color = team_colors.get(team, "#888")
                    with col:
                        st.markdown(
                            f"""
                            <div style="background:rgba(255,255,255,0.07);border:2px solid {color};
                                        border-radius:12px;padding:14px;text-align:center;">
                                <div style="color:{color};font-weight:900;font-size:1.1rem;">{team}</div>
                                <div style="margin-top:8px;font-size:0.85rem;color:rgba(255,255,255,0.8);">
                                    {'<br>'.join(members)}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    # ── 탭3: 타수 입력 & 저장
    with tab3:
        st.markdown('<div class="section-header">최종 타수 입력</div>', unsafe_allow_html=True)

        if not st.session_state["players"]:
            st.warning("⚠️ 먼저 [② 참가자 등록] 탭에서 참가자를 추가해주세요.")
        else:
            st.info(f"총 {len(st.session_state['players'])}명의 타수를 입력해주세요.")
            n = len(st.session_state["players"])
            num_cols = min(n, 4)
            score_cols = st.columns(num_cols)
            updated_players = list(st.session_state["players"])

            for i, player in enumerate(updated_players):
                col_idx = i % num_cols
                with score_cols[col_idx]:
                    team_str = f" ({player['team']})" if player.get("team") else ""
                    score = st.number_input(
                        f"🏌️ {player['name']}{team_str}\n핸디: {player['handicap']}",
                        min_value=40,
                        max_value=180,
                        value=int(player.get("score") or 72),
                        key=f"score_{i}_{player['name']}",
                    )
                    updated_players[i] = {**player, "score": score}

            st.session_state["players"] = updated_players

            # 미리보기
            st.markdown('<div class="section-header">순점 미리보기</div>', unsafe_allow_html=True)
            preview_data = [
                {
                    "이름": p["name"],
                    "팀": p.get("team") or "-",
                    "핸디": p["handicap"],
                    "타수": p["score"],
                    "결과 (vs 72타)": f"+{p['score'] - 72}" if p["score"] - 72 > 0 else str(p["score"] - 72) if p["score"] - 72 < 0 else "E",
                    "순점 (타수-핸디)": p["score"] - p["handicap"],
                }
                for p in updated_players
            ]
            preview_df = pd.DataFrame(preview_data).sort_values("순점 (타수-핸디)")
            st.dataframe(preview_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            if st.button("💾 경기 결과 최종 저장", use_container_width=True, type="primary"):
                if "current_game_meta" not in st.session_state:
                    st.error("먼저 [① 경기 정보] 탭에서 경기 정보를 저장해주세요!")
                else:
                    meta = st.session_state["current_game_meta"]
                    players = st.session_state["players"]

                    # 순위/승패 계산
                    if meta["mode"] == "개인전":
                        for p in players:
                            p["net_score"] = p["score"] - p["handicap"]
                        sorted_p = sorted(players, key=lambda x: x["net_score"])
                        for rank, p in enumerate(sorted_p, 1):
                            for orig in players:
                                if orig["name"] == p["name"]:
                                    orig["rank"] = rank
                                    break
                    else:
                        team_df = calc_team_ranking(players)
                        winner_team = team_df.iloc[0]["team"]
                        for p in players:
                            p["net_score"] = p["score"] - p["handicap"]
                            p["is_winner"] = p["team"] == winner_team
                            p["rank"] = 1 if p["is_winner"] else 2

                    # 저장
                    games = load_json(GAMES_FILE)
                    game_record = {**meta, "player_count": len(players)}
                    # 중복 저장 방지
                    if not any(g["game_id"] == meta["game_id"] for g in games):
                        games.append(game_record)
                        save_json(GAMES_FILE, games)

                    results = load_json(RESULTS_FILE)
                    # 중복 저장 방지
                    existing_ids = {r["game_id"] for r in results}
                    if meta["game_id"] not in existing_ids:
                        for p in players:
                            results.append(
                                {
                                    "game_id": meta["game_id"],
                                    "date": meta["date"],
                                    "venue": meta["venue"],
                                    "field": meta["field"],
                                    "mode": meta["mode"],
                                    "name": p["name"],
                                    "handicap": p["handicap"],
                                    "score": p["score"],
                                    "net_score": p.get("net_score", p["score"] - p["handicap"]),
                                    "team": p.get("team"),
                                    "rank": p.get("rank"),
                                    "is_winner": p.get("is_winner"),
                                }
                            )
                        save_json(RESULTS_FILE, results)

                    st.success("🎉 경기 결과가 성공적으로 저장되었습니다!")
                    st.balloons()
                    # 초기화
                    st.session_state["players"] = []
                    st.session_state["current_game_id"] = None
                    if "current_game_meta" in st.session_state:
                        del st.session_state["current_game_meta"]


# ══════════════════════════════════════════
# 2. 결과 확인
# ══════════════════════════════════════════
elif "결과 확인" in menu:
    st.markdown('<div class="main-title">📊 경기 결과</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Game Results</div>', unsafe_allow_html=True)

    results_df = get_results_df()
    games_df = get_games_df()

    if results_df.empty or games_df.empty:
        st.info("아직 저장된 경기 결과가 없습니다. 경기를 먼저 입력해주세요!")
    else:
        game_options = games_df.apply(
            lambda r: f"[{r['date']}] {r['venue']} - {r['field']} ({r['mode']})", axis=1
        ).tolist()
        selected_idx = st.selectbox(
            "경기 선택", range(len(game_options)), format_func=lambda i: game_options[i]
        )
        selected_game = games_df.iloc[selected_idx]
        game_id = selected_game["game_id"]
        game_results = results_df[results_df["game_id"] == game_id].copy()
        game_results["net_score"] = pd.to_numeric(game_results["net_score"], errors="coerce")
        game_results["score"] = pd.to_numeric(game_results["score"], errors="coerce")
        game_results["handicap"] = pd.to_numeric(game_results["handicap"], errors="coerce")

        st.markdown(
            f"""
            <div class="golf-card">
                <div style="display:flex;gap:30px;flex-wrap:wrap;color:rgba(255,255,255,0.9);">
                    <div>📅 <b>{selected_game['date']}</b></div>
                    <div>🏢 <b>{selected_game['venue']}</b></div>
                    <div>🌿 <b>{selected_game['field']}</b></div>
                    <div>🎯 <b>{selected_game['mode']}</b></div>
                    <div>👥 <b>{selected_game['player_count']}명</b></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if selected_game["mode"] == "개인전":
            st.markdown('<div class="section-header">🏆 개인전 순위</div>', unsafe_allow_html=True)
            sorted_results = game_results.sort_values("net_score").reset_index(drop=True)
            medal_map = {0: "🥇", 1: "🥈", 2: "🥉"}
            for i, row in sorted_results.iterrows():
                medal = medal_map.get(i, f"{i + 1}위")
                st.markdown(
                    f"""
                    <div class="golf-card" style="display:flex;justify-content:space-between;align-items:center;padding:16px 24px;">
                        <div style="font-size:1.5rem;">{medal}</div>
                        <div style="font-size:1.1rem;font-weight:700;color:white;">{row['name']}</div>
                        <div style="color:rgba(255,255,255,0.6);">핸디: {row['handicap']:.1f}</div>
                        <div style="color:rgba(255,255,255,0.6);">타수: {int(row['score'])}</div>
                        <div style="color:{'#EB5757' if int(row['score']) - 72 > 0 else '#27AE60' if int(row['score']) - 72 < 0 else '#F2C94C'};font-weight:700;">
                            결과: {'+' + str(int(row['score']) - 72) if int(row['score']) - 72 > 0 else 'E' if int(row['score']) - 72 == 0 else str(int(row['score']) - 72)}
                        </div>
                        <div style="color:#56CCF2;font-weight:900;font-size:1.2rem;">순점: {int(row['net_score'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            fig = px.bar(
                sorted_results,
                x="name", y="net_score",
                color="net_score",
                color_continuous_scale=["#27AE60", "#F2C94C", "#EB5757"],
                title="개인별 순점수 (낮을수록 우승)",
                labels={"name": "이름", "net_score": "순점수"},
                text="net_score",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        else:  # 팀전
            st.markdown('<div class="section-header">🏆 팀전 결과</div>', unsafe_allow_html=True)
            team_summary = (
                game_results.groupby("team")
                .agg(
                    total_score=("score", "sum"),
                    total_handicap=("handicap", "sum"),
                    members=("name", lambda x: ", ".join(x)),
                )
                .reset_index()
            )
            team_summary["net_score"] = team_summary["total_score"] - team_summary["total_handicap"]
            team_summary = team_summary.sort_values("net_score").reset_index(drop=True)

            winner = team_summary.iloc[0]["team"]
            st.markdown(
                f'<div class="win-banner">🏆 {winner} 승리!</div>',
                unsafe_allow_html=True,
            )

            team_colors_map = {
                "A팀": "#2F80ED", "B팀": "#EB5757", "C팀": "#27AE60", "D팀": "#9B51E0",
            }
            for i, row in team_summary.iterrows():
                rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else f"{i + 1}위"
                color = team_colors_map.get(row["team"], "#888")
                st.markdown(
                    f"""
                    <div class="golf-card">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                            <div style="font-size:1.3rem;">{rank_emoji}
                                <span style="color:{color};font-weight:900;margin-left:8px;">{row['team']}</span>
                            </div>
                            <div style="color:rgba(255,255,255,0.7);">구성: {row['members']}</div>
                            <div style="color:rgba(255,255,255,0.7);">합산 타수: {int(row['total_score'])}</div>
                            <div style="color:{'#EB5757' if int(row['total_score']) - 72 > 0 else '#27AE60' if int(row['total_score']) - 72 < 0 else '#F2C94C'};font-weight:700;">
                                결과: {'+' + str(int(row['total_score']) - 72) if int(row['total_score']) - 72 > 0 else 'E' if int(row['total_score']) - 72 == 0 else str(int(row['total_score']) - 72)}
                            </div>
                            <div style="color:rgba(255,255,255,0.7);">합산 핸디: {row['total_handicap']:.1f}</div>
                            <div style="color:#56CCF2;font-weight:900;font-size:1.2rem;">순점: {int(row['net_score'])}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="section-header">개인별 타수 상세</div>', unsafe_allow_html=True)
            detail_df = game_results[["team", "name", "handicap", "score", "net_score"]].copy()
            detail_df.columns = ["팀", "이름", "핸디", "타수", "순점"]
            detail_df = detail_df.sort_values(["팀", "순점"])
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

            # 팀 비교 차트
            fig_team = px.bar(
                team_summary,
                x="team", y="net_score",
                color="team",
                color_discrete_sequence=["#2F80ED", "#EB5757", "#27AE60", "#9B51E0"],
                title="팀별 순점수 비교 (낮을수록 승리)",
                labels={"team": "팀", "net_score": "팀 순점수"},
                text="net_score",
            )
            fig_team.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
            )
            st.plotly_chart(fig_team, use_container_width=True)

        # ── 결과 수정 기능
        st.markdown("---")
        st.markdown('<div class="section-header">✏️ 결과 수정</div>', unsafe_allow_html=True)
        player_names = game_results["name"].tolist()
        edit_player = st.selectbox("수정할 선수 선택", player_names, key="edit_player_select")
        if edit_player:
            player_row = game_results[game_results["name"] == edit_player].iloc[0]
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                edit_score = st.number_input(
                    "타수", min_value=40, max_value=180,
                    value=int(player_row["score"]), key=f"edit_score_{edit_player}"
                )
            with col_e2:
                edit_handi = st.number_input(
                    "G핸디", min_value=-30.0, max_value=50.0,
                    value=float(player_row["handicap"]), step=0.1, format="%.1f", key=f"edit_handi_{edit_player}"
                )
            with col_e3:
                if selected_game["mode"] == "팀전":
                    team_options = ["A팀", "B팀", "C팀", "D팀"]
                    cur_team = player_row.get("team") or "A팀"
                    edit_team = st.selectbox("팀", team_options,
                                             index=team_options.index(cur_team) if cur_team in team_options else 0,
                                             key=f"edit_team_{edit_player}")
                else:
                    edit_team = None
                    st.write("")

            if st.button("💾 수정 저장", use_container_width=True, type="primary"):
                results_all = load_json(RESULTS_FILE)
                new_net = edit_score - edit_handi
                for r in results_all:
                    if r["game_id"] == game_id and r["name"] == edit_player:
                        r["score"] = edit_score
                        r["handicap"] = edit_handi
                        r["net_score"] = new_net
                        if edit_team is not None:
                            r["team"] = edit_team
                # 순위 재계산
                game_records = [r for r in results_all if r["game_id"] == game_id]
                if selected_game["mode"] == "개인전":
                    sorted_r = sorted(game_records, key=lambda x: x["net_score"])
                    for rank_i, r in enumerate(sorted_r, 1):
                        for orig in results_all:
                            if orig["game_id"] == game_id and orig["name"] == r["name"]:
                                orig["rank"] = rank_i
                                break
                else:
                    from collections import defaultdict
                    team_nets = defaultdict(float)
                    for r in game_records:
                        team_nets[r["team"]] += r["net_score"]
                    winner_team = min(team_nets, key=team_nets.get)
                    for orig in results_all:
                        if orig["game_id"] == game_id:
                            orig["is_winner"] = orig["team"] == winner_team
                            orig["rank"] = 1 if orig["is_winner"] else 2
                save_json(RESULTS_FILE, results_all)
                st.success(f"✅ {edit_player} 결과가 수정되었습니다!")
                st.rerun()


# ══════════════════════════════════════════
# 3. 누적 통계
# ══════════════════════════════════════════
elif "누적 통계" in menu:
    st.markdown('<div class="main-title">📈 누적 통계</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cumulative Statistics</div>', unsafe_allow_html=True)

    results_df = get_results_df()

    if results_df.empty:
        st.info("아직 데이터가 없습니다. 경기를 입력하면 통계가 생성됩니다.")
    else:
        results_df["net_score"] = pd.to_numeric(results_df["net_score"], errors="coerce")
        results_df["score"] = pd.to_numeric(results_df["score"], errors="coerce")

        stat_tab1, stat_tab2, stat_tab3, stat_tab4 = st.tabs(
            ["👤 개인별 통계", "🎯 G핸디별 분석", "👥 팀별 분석", "📊 경기 트렌드"]
        )

        # ── 공통 전처리 ─────────────────────────────
        results_df["handicap"] = pd.to_numeric(results_df["handicap"], errors="coerce")
        results_df["rank"] = pd.to_numeric(results_df["rank"], errors="coerce")

        _chart_layout = dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )

        # ── Tab 1: 개인별 통계 ──────────────────────
        with stat_tab1:
            st.markdown('<div class="section-header">개인별 성적 요약</div>', unsafe_allow_html=True)

            player_stats = (
                results_df.groupby("name")
                .agg(
                    경기수=("game_id", "nunique"),
                    평균타수=("score", "mean"),
                    평균순점=("net_score", "mean"),
                    최저타수=("score", "min"),
                    최고타수=("score", "max"),
                    순점편차=("net_score", "std"),
                )
                .round(1)
                .reset_index()
                .sort_values("평균순점")
            )

            # 최근 3경기 평균 (날짜 기준)
            recent_avg = []
            for name, grp in results_df.sort_values("date").groupby("name"):
                last3 = grp.tail(3)["net_score"].mean()
                recent_avg.append({"name": name, "최근3경기평균": round(last3, 1)})
            player_stats = player_stats.merge(pd.DataFrame(recent_avg), on="name", how="left")

            # 개인전 우승 횟수
            indiv = results_df[results_df["mode"] == "개인전"].copy()
            if not indiv.empty:
                wins = (
                    indiv[indiv["rank"] == 1]
                    .groupby("name").size().reset_index(name="우승횟수")
                )
                total_games_per_player = (
                    indiv.groupby("name")["game_id"].nunique().reset_index(name="개인전경기수")
                )
                win_stats = wins.merge(total_games_per_player, on="name", how="right").fillna(0)
                win_stats["우승횟수"] = win_stats["우승횟수"].astype(int)
                win_stats["승률(%)"] = (
                    win_stats["우승횟수"] / win_stats["개인전경기수"] * 100
                ).round(1)
                player_stats = player_stats.merge(
                    win_stats[["name", "우승횟수", "승률(%)"]],
                    on="name", how="left",
                ).fillna(0)

            st.dataframe(
                player_stats.rename(columns={"name": "이름"}),
                use_container_width=True,
                hide_index=True,
            )

            # 평균 순점 차트
            fig_bar = px.bar(
                player_stats.sort_values("평균순점"),
                x="name", y="평균순점",
                color="평균순점",
                color_continuous_scale=["#27AE60", "#F2C94C", "#EB5757"],
                title="개인별 평균 순점수 (낮을수록 우수)",
                labels={"name": "이름", "평균순점": "평균 순점수"},
                text="평균순점",
            )
            fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_bar.update_layout(**_chart_layout)
            st.plotly_chart(fig_bar, use_container_width=True)

            # 최근 3경기 vs 전체 평균 비교
            if len(player_stats) >= 2:
                st.markdown('<div class="section-header">최근 3경기 vs 전체 평균 비교</div>', unsafe_allow_html=True)
                compare_df = player_stats[["name", "평균순점", "최근3경기평균"]].dropna()
                fig_cmp = go.Figure()
                fig_cmp.add_trace(go.Bar(
                    name="전체 평균", x=compare_df["name"], y=compare_df["평균순점"],
                    marker_color="#2F80ED", text=compare_df["평균순점"],
                    texttemplate="%{text:.1f}", textposition="outside",
                ))
                fig_cmp.add_trace(go.Bar(
                    name="최근 3경기", x=compare_df["name"], y=compare_df["최근3경기평균"],
                    marker_color="#F2C94C", text=compare_df["최근3경기평균"],
                    texttemplate="%{text:.1f}", textposition="outside",
                ))
                fig_cmp.update_layout(
                    barmode="group", title="전체 평균 vs 최근 3경기 순점",
                    **_chart_layout,
                )
                st.plotly_chart(fig_cmp, use_container_width=True)

            # 레이더 차트
            if len(player_stats) >= 3:
                st.markdown('<div class="section-header">선수 능력치 레이더</div>', unsafe_allow_html=True)
                top_n = player_stats.head(min(5, len(player_stats)))
                fig_radar = go.Figure()
                min_net = results_df["net_score"].min()
                max_net = results_df["net_score"].max()
                max_games = player_stats["경기수"].max()
                min_score = results_df["score"].min()
                max_score_val = results_df["score"].max()
                max_std = player_stats["순점편차"].max() if player_stats["순점편차"].max() > 0 else 1
                categories = ["타수(역산)", "순점(역산)", "경기참여도", "안정성"]

                for _, row in top_n.iterrows():
                    score_norm = (max_score_val - row["평균타수"]) / max(max_score_val - min_score, 1) * 100
                    net_norm = (max_net - row["평균순점"]) / max(max_net - min_net, 1) * 100
                    game_norm = row["경기수"] / max(max_games, 1) * 100
                    std_val = row["순점편차"] if pd.notna(row["순점편차"]) else max_std
                    stability = (1 - std_val / max_std) * 100
                    vals = [score_norm, net_norm, game_norm, stability]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=categories + [categories[0]],
                        fill="toself", name=row["name"], opacity=0.75,
                    ))
                fig_radar.update_layout(
                    polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0, 100])),
                    paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                    title="선수별 레이더 차트 (Top 5)",
                )
                st.plotly_chart(fig_radar, use_container_width=True)

        # ── Tab 2: G핸디별 분석 ────────────────────
        with stat_tab2:
            st.markdown('<div class="section-header">G핸디 구간별 성적 분석</div>', unsafe_allow_html=True)

            def handi_label(h):
                if h < 0:
                    return "마이너스 (<0)"
                elif h < 5:
                    return "로우 (0~4)"
                elif h < 10:
                    return "미들로우 (5~9)"
                elif h < 15:
                    return "미들 (10~14)"
                elif h < 20:
                    return "미들하이 (15~19)"
                else:
                    return "하이 (20+)"

            handi_order = ["마이너스 (<0)", "로우 (0~4)", "미들로우 (5~9)",
                           "미들 (10~14)", "미들하이 (15~19)", "하이 (20+)"]

            rdf = results_df.copy()
            rdf["핸디구간"] = rdf["handicap"].apply(handi_label)

            handi_stats = (
                rdf.groupby("핸디구간")
                .agg(
                    인원수=("name", "nunique"),
                    참가횟수=("game_id", "count"),
                    평균타수=("score", "mean"),
                    평균순점=("net_score", "mean"),
                    평균핸디=("handicap", "mean"),
                    최저순점=("net_score", "min"),
                )
                .round(1)
                .reset_index()
            )
            handi_stats["핸디구간"] = pd.Categorical(
                handi_stats["핸디구간"], categories=handi_order, ordered=True
            )
            handi_stats = handi_stats.sort_values("핸디구간")

            st.dataframe(handi_stats, use_container_width=True, hide_index=True)

            fig_h1 = px.bar(
                handi_stats, x="핸디구간", y="평균순점",
                color="평균순점",
                color_continuous_scale=["#27AE60", "#F2C94C", "#EB5757"],
                title="핸디 구간별 평균 순점수",
                text="평균순점",
            )
            fig_h1.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_h1.update_layout(**_chart_layout)
            st.plotly_chart(fig_h1, use_container_width=True)

            fig_h2 = px.scatter(
                rdf, x="handicap", y="net_score",
                color="name", hover_data=["date", "score"],
                trendline="ols",
                title="G핸디 vs 순점 분포 (추세선 포함)",
                labels={"handicap": "G핸디", "net_score": "순점", "name": "선수"},
            )
            fig_h2.update_layout(**_chart_layout)
            st.plotly_chart(fig_h2, use_container_width=True)

            # 개인별 핸디 변화 추이 (핸디가 여러 경기에서 다른 경우)
            handi_trend = (
                rdf.sort_values("date")
                .groupby(["name", "date"])["handicap"]
                .mean()
                .reset_index()
            )
            handi_names = handi_trend["name"].unique().tolist()
            if len(handi_names) >= 2:
                st.markdown('<div class="section-header">선수별 G핸디 변화 추이</div>', unsafe_allow_html=True)
                sel_h = st.multiselect(
                    "선수 선택 (핸디 추이)", handi_names,
                    default=handi_names[:min(4, len(handi_names))],
                    key="handi_trend_sel",
                )
                if sel_h:
                    fig_h3 = px.line(
                        handi_trend[handi_trend["name"].isin(sel_h)],
                        x="date", y="handicap", color="name", markers=True,
                        title="선수별 G핸디 변화",
                        labels={"date": "날짜", "handicap": "G핸디", "name": "선수"},
                    )
                    fig_h3.update_layout(**_chart_layout)
                    st.plotly_chart(fig_h3, use_container_width=True)

        # ── Tab 3: 팀별 분석 ───────────────────────
        with stat_tab3:
            team_df_raw = results_df[
                (results_df["mode"] == "팀전") & results_df["team"].notna()
            ].copy()

            if team_df_raw.empty:
                st.info("팀전 경기 데이터가 없습니다.")
            else:
                st.markdown('<div class="section-header">팀별 성적 요약</div>', unsafe_allow_html=True)

                # 경기별 팀 순위 → 우승 집계
                game_team = (
                    team_df_raw.groupby(["game_id", "date", "team"])
                    .agg(
                        팀순점=("net_score", "sum"),
                        팀타수=("score", "sum"),
                        팀핸디=("handicap", "sum"),
                        인원=("name", "nunique"),
                    )
                    .reset_index()
                )
                game_team["팀순위"] = (
                    game_team.groupby("game_id")["팀순점"]
                    .rank(method="min", ascending=True)
                    .astype(int)
                )

                team_summary = (
                    game_team.groupby("team")
                    .agg(
                        경기수=("game_id", "nunique"),
                        우승횟수=("팀순위", lambda x: (x == 1).sum()),
                        평균팀순점=("팀순점", "mean"),
                        평균팀타수=("팀타수", "mean"),
                        평균팀핸디=("팀핸디", "mean"),
                    )
                    .round(1)
                    .reset_index()
                )
                team_summary["승률(%)"] = (
                    team_summary["우승횟수"] / team_summary["경기수"] * 100
                ).round(1)
                team_summary = team_summary.sort_values("승률(%)", ascending=False)

                st.dataframe(team_summary.rename(columns={"team": "팀"}),
                             use_container_width=True, hide_index=True)

                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    fig_twin = px.bar(
                        team_summary, x="team", y="우승횟수",
                        color="team", title="팀별 우승 횟수",
                        labels={"team": "팀", "우승횟수": "우승 횟수"},
                        color_discrete_map={
                            "A팀": "#2F80ED", "B팀": "#EB5757",
                            "C팀": "#27AE60", "D팀": "#9B51E0",
                        },
                        text="우승횟수",
                    )
                    fig_twin.update_traces(textposition="outside")
                    fig_twin.update_layout(**_chart_layout)
                    st.plotly_chart(fig_twin, use_container_width=True)
                with col_t2:
                    fig_tnet = px.bar(
                        team_summary.sort_values("평균팀순점"),
                        x="team", y="평균팀순점",
                        color="team", title="팀별 평균 팀순점 (낮을수록 강팀)",
                        labels={"team": "팀", "평균팀순점": "평균 팀순점"},
                        color_discrete_map={
                            "A팀": "#2F80ED", "B팀": "#EB5757",
                            "C팀": "#27AE60", "D팀": "#9B51E0",
                        },
                        text="평균팀순점",
                    )
                    fig_tnet.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                    fig_tnet.update_layout(**_chart_layout)
                    st.plotly_chart(fig_tnet, use_container_width=True)

                # 경기별 팀 순점 변화
                st.markdown('<div class="section-header">경기별 팀 순점 변화 추이</div>', unsafe_allow_html=True)
                fig_tline = px.line(
                    game_team.sort_values("date"),
                    x="date", y="팀순점", color="team", markers=True,
                    title="경기별 팀 순점 변화",
                    labels={"date": "날짜", "팀순점": "팀 순점", "team": "팀"},
                    color_discrete_map={
                        "A팀": "#2F80ED", "B팀": "#EB5757",
                        "C팀": "#27AE60", "D팀": "#9B51E0",
                    },
                )
                fig_tline.update_layout(**_chart_layout)
                st.plotly_chart(fig_tline, use_container_width=True)

                # 팀원별 기여도 (팀전 개인 순점)
                st.markdown('<div class="section-header">팀전 선수별 기여도 (평균 순점)</div>', unsafe_allow_html=True)
                contrib = (
                    team_df_raw.groupby(["team", "name"])
                    .agg(평균순점=("net_score", "mean"), 경기수=("game_id", "nunique"))
                    .round(1).reset_index()
                    .sort_values(["team", "평균순점"])
                )
                fig_contrib = px.bar(
                    contrib, x="name", y="평균순점", color="team",
                    title="팀전 선수별 평균 순점 (낮을수록 기여도 높음)",
                    labels={"name": "선수", "평균순점": "평균 순점", "team": "팀"},
                    color_discrete_map={
                        "A팀": "#2F80ED", "B팀": "#EB5757",
                        "C팀": "#27AE60", "D팀": "#9B51E0",
                    },
                    text="평균순점", barmode="group",
                )
                fig_contrib.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig_contrib.update_layout(**_chart_layout)
                st.plotly_chart(fig_contrib, use_container_width=True)

        # ── Tab 4: 경기 트렌드 ─────────────────────
        with stat_tab4:
            st.markdown('<div class="section-header">경기별 순점 변화 추이</div>', unsafe_allow_html=True)

            all_players = sorted(results_df["name"].unique().tolist())
            selected_players = st.multiselect(
                "선수 선택",
                all_players,
                default=all_players[: min(3, len(all_players))],
            )

            if selected_players:
                trend_data = results_df[results_df["name"].isin(selected_players)].copy()
                trend_data = trend_data.sort_values("date")

                fig_line = px.line(
                    trend_data,
                    x="date", y="net_score", color="name", markers=True,
                    title="경기별 순점수 변화",
                    labels={"date": "날짜", "net_score": "순점수", "name": "선수"},
                )
                fig_line.update_layout(**_chart_layout)
                st.plotly_chart(fig_line, use_container_width=True)

            # 월별 경기 수
            monthly = (
                results_df.assign(month=results_df["date"].str[:7])
                .groupby("month")["game_id"]
                .nunique()
                .reset_index(name="경기수")
            )
            if not monthly.empty:
                fig_monthly = px.area(
                    monthly, x="month", y="경기수",
                    title="월별 경기 수",
                    labels={"month": "월", "경기수": "경기 수"},
                    color_discrete_sequence=["#2F80ED"],
                )
                fig_monthly.update_layout(**_chart_layout)
                st.plotly_chart(fig_monthly, use_container_width=True)


# ══════════════════════════════════════════
# 4. 전체 경기 기록
# ══════════════════════════════════════════
elif "경기 기록" in menu:
    st.markdown('<div class="main-title">📋 전체 경기 기록</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">All Game Records</div>', unsafe_allow_html=True)

    games_df = get_games_df()
    results_df = get_results_df()

    if games_df.empty:
        st.info("아직 저장된 경기 기록이 없습니다.")
    else:
        st.markdown(f"**총 {len(games_df)}경기** 기록되어 있습니다.")

        col1, col2 = st.columns(2)
        with col1:
            search_venue = st.text_input("🔍 장소 검색", "")
        with col2:
            filter_mode = st.selectbox("경기 방식 필터", ["전체", "개인전", "팀전"])

        filtered = games_df.copy()
        if search_venue:
            filtered = filtered[filtered["venue"].str.contains(search_venue, na=False)]
        if filter_mode != "전체":
            filtered = filtered[filtered["mode"] == filter_mode]

        filtered_display = filtered[["date", "venue", "field", "mode", "player_count"]].copy()
        filtered_display.columns = ["날짜", "장소", "필드", "경기방식", "참가인원"]
        st.dataframe(
            filtered_display.sort_values("날짜", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        if not results_df.empty:
            st.markdown('<div class="section-header">전체 결과 상세</div>', unsafe_allow_html=True)
            show_cols = ["date", "venue", "mode", "name", "handicap", "score", "net_score", "team", "rank"]
            detail = results_df[[c for c in show_cols if c in results_df.columns]].copy()
            detail.columns = [
                {"date": "날짜", "venue": "장소", "mode": "방식", "name": "이름",
                 "handicap": "핸디", "score": "타수", "net_score": "순점",
                 "team": "팀", "rank": "순위"}.get(c, c)
                for c in detail.columns
            ]
            st.dataframe(detail.sort_values("날짜", ascending=False), use_container_width=True, hide_index=True)

            # CSV 다운로드
            csv_data = results_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 전체 결과 CSV 다운로드",
                data=csv_data,
                file_name="golf_results_all.csv",
                mime="text/csv",
            )

            # 경기 삭제 기능
            st.markdown('<div class="section-header">경기 삭제</div>', unsafe_allow_html=True)
            st.warning("⚠️ 삭제된 경기는 복구할 수 없습니다.")
            game_options = games_df.apply(
                lambda r: f"[{r['date']}] {r['venue']} ({r['game_id']})", axis=1
            ).tolist()
            del_idx = st.selectbox("삭제할 경기", range(len(game_options)), format_func=lambda i: game_options[i])
            if st.button("🗑️ 선택 경기 삭제", type="secondary"):
                del_id = games_df.iloc[del_idx]["game_id"]
                new_games = [g for g in load_json(GAMES_FILE) if g["game_id"] != del_id]
                new_results = [r for r in load_json(RESULTS_FILE) if r["game_id"] != del_id]
                save_json(GAMES_FILE, new_games)
                save_json(RESULTS_FILE, new_results)
                st.success("삭제 완료!")
                st.rerun()


# ══════════════════════════════════════════
# 5. 선수 관리
# ══════════════════════════════════════════
elif "선수 관리" in menu:
    st.markdown('<div class="main-title">👥 선수 관리</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Player Roster Management</div>', unsafe_allow_html=True)

    roster = get_players_roster()

    # 신규 선수 등록
    st.markdown('<div class="section-header">신규 선수 등록</div>', unsafe_allow_html=True)
    col_n1, col_n2, col_n3 = st.columns([2, 1, 1])
    with col_n1:
        new_pname = st.text_input("👤 이름", key="roster_new_name")
    with col_n2:
        new_phandi = st.number_input(
            "🎯 G핸디", min_value=-30.0, max_value=50.0, value=0.0, step=0.1, format="%.1f", key="roster_new_handi"
        )
    with col_n3:
        st.write("")
        st.write("")
        if st.button("➕ 등록", use_container_width=True):
            if not new_pname.strip():
                st.error("이름을 입력해주세요!")
            elif any(p["name"] == new_pname.strip() for p in roster):
                st.error("이미 등록된 선수입니다!")
            else:
                roster.append({"name": new_pname.strip(), "handicap": new_phandi})
                save_players_roster(roster)
                st.success(f"✅ {new_pname.strip()} 등록 완료!")
                st.rerun()

    # 등록된 선수 목록 & 수정/삭제
    st.markdown('<div class="section-header">등록된 선수 목록</div>', unsafe_allow_html=True)
    if not roster:
        st.info("등록된 선수가 없습니다. 선수를 추가해주세요.")
    else:
        header_cols = st.columns([3, 2, 2, 1, 1])
        header_cols[0].markdown("**이름**")
        header_cols[1].markdown("**G핸디**")
        header_cols[2].markdown("**수정**")
        header_cols[3].markdown("")
        header_cols[4].markdown("")

        for i, player in enumerate(roster):
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
            with c1:
                st.write(f"**{player['name']}**")
            with c2:
                edit_h = st.number_input(
                    "", min_value=-30.0, max_value=50.0,
                    value=float(player["handicap"]), step=0.1, format="%.1f",
                    key=f"roster_handi_{i}",
                    label_visibility="collapsed"
                )
            with c3:
                edit_n = st.text_input(
                    "", value=player["name"], key=f"roster_name_{i}",
                    label_visibility="collapsed"
                )
            with c4:
                if st.button("💾", key=f"roster_save_{i}", help="저장"):
                    if not edit_n.strip():
                        st.error("이름을 입력해주세요!")
                    elif edit_n.strip() != player["name"] and any(p["name"] == edit_n.strip() for p in roster):
                        st.error("이미 같은 이름의 선수가 있습니다!")
                    else:
                        roster[i]["name"] = edit_n.strip()
                        roster[i]["handicap"] = edit_h
                        save_players_roster(roster)
                        st.success(f"✅ {edit_n.strip()} 정보 수정 완료!")
                        st.rerun()
            with c5:
                if st.button("❌", key=f"roster_del_{i}", help="삭제"):
                    roster.pop(i)
                    save_players_roster(roster)
                    st.rerun()
