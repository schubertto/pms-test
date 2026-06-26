# -*- coding: utf-8 -*-
"""
팀 프로젝트 진행상황 관리 시스템(PMS) - 메인 Streamlit 어플리케이션
디자인 시스템, WBS, 갠트 차트(Plotly), 칸반 보드 및 Neon DB CRUD 완비 버전
작성자: Antigravity AI
"""

import os
import datetime
import warnings
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from dotenv import load_dotenv

# 1. Pandas DB 연결 경고 메시지 무시 설정
warnings.filterwarnings('ignore')

# 2. 입구에서 검사 (Early Return) - 환경 설정 검증
env_path = '.env.local'
if not os.path.exists(env_path):
    st.error("`.env.local` 파일이 존재하지 않습니다. db_setup.py를 실행했는지 확인해주세요.")
    st.stop()

load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL 환경 변수가 누락되었습니다. `.env.local` 파일을 점검해주세요.")
    st.stop()

# ==========================================
# [디자인 설정 및 초기화]
# ==========================================

# 페이지 설정
st.set_page_config(
    page_title="애자일 팀 프로젝트 관리 (PMS)",
    page_icon="⛵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 테마 상태 관리 초기화
if "theme" not in st.session_state:
    st.session_state.theme = "light" # 기본 테마 모드를 일반(라이트) 모드로 변경합니다.

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    print(f"[테마 변경] 사용자 요청으로 UI 테마가 {st.session_state.theme} 모드로 전환되었습니다.")

IS_DARK = st.session_state.theme == "dark"

# 디자인 토큰 색상 정의
BG_COLOR = "#09090b" if IS_DARK else "#ffffff"
CARD_BG = "#0c0c0f" if IS_DARK else "#f9fafb"
BORDER_COLOR = "#1e1e24" if IS_DARK else "#e4e4e7"
TEXT_COLOR = "#fafafa" if IS_DARK else "#09090b"
TEXT_MUTED = "#71717a" if IS_DARK else "#52525b"
ACCENT_BLUE = "#2563eb"
ACCENT_GREEN = "#22c55e"
ACCENT_ORANGE = "#f97316"

# 커스텀 CSS 주입
# [확인용 출력] 디자인 시스템 주입 및 사이드바 토글 버튼 상태 점검 로그
print("[디자인 시스템] 사이드바 열기 버튼 활성화가 적용된 CSS 스타일을 주입합니다.")
st.markdown(f"""
<style>
    /* Streamlit 기본 메뉴 및 푸터 숨김 (헤더는 사이드바 열기 버튼을 위해 투명화 노출) */
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
        pointer-events: none; /* 클릭 이벤트가 하단 콘텐츠로 통과되도록 처리 */
    }}
    header[data-testid="stHeader"] button {{
        pointer-events: auto; /* 사이드바 토글(열기/닫기) 버튼은 클릭 가능하도록 처리 */
    }}
    #MainMenu, footer, .stDeployButton {{
        display: none !important;
    }}
    
    /* 전체 배경 스타일 커스텀 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
        background-color: {BG_COLOR} !important;
        color: {TEXT_COLOR} !important;
        font-family: 'Inter', -apple-system, sans-serif;
    }}
    
    /* 세련된 대시보드 카드 스타일 */
    .pms-card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.25rem;
    }}
    .pms-card-label {{
        font-size: 0.8rem;
        color: {TEXT_MUTED};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .pms-card-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {TEXT_COLOR};
        margin-top: 0.25rem;
    }}
    
    /* 칸반보드 리스트 스타일 */
    .kanban-col {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 10px;
        padding: 1rem;
        min-height: 150px;
    }}
    .kanban-header {{
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {BORDER_COLOR};
    }}
    .kanban-card {{
        background-color: {"#18181b" if IS_DARK else "#ffffff"};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        padding: 0.85rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .kanban-card-title {{
        font-size: 0.9rem;
        font-weight: 600;
        color: {TEXT_COLOR};
        margin-bottom: 0.25rem;
    }}
    .kanban-card-meta {{
        font-size: 0.75rem;
        color: {TEXT_MUTED};
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# [데이터베이스 CRUD 인터페이스]
# ==========================================

def get_connection():
    """데이터베이스 연결 객체를 안전하게 반환합니다."""
    return psycopg2.connect(DATABASE_URL)

def db_query(query, params=None):
    """SELECT 쿼리를 수행하고 판다스 DataFrame으로 반환합니다."""
    print(f"[DB SELECT] Query: {query} | Params: {params}")
    try:
        with get_connection() as conn:
            return pd.read_sql(query, conn, params=params)
    except Exception as e:
        st.error(f"데이터베이스 조회 오류: {e}")
        return pd.DataFrame()

def db_execute(query, params=None):
    """INSERT, UPDATE, DELETE 등 쓰기 작업을 수행합니다."""
    print(f"[DB WRITE] Query: {query} | Params: {params}")
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"데이터베이스 처리 오류: {e}")
        return False

# ==========================================
# [검증 및 비즈니스 로직 함수]
# ==========================================

def is_wbs_code_duplicate(wbs_code, current_task_id=None):
    """동일한 WBS 코드가 데이터베이스에 이미 존재하는지 검사합니다."""
    if current_task_id:
        df = db_query("SELECT id FROM pms_tasks WHERE wbs_code = %s AND id != %s LIMIT 1;", (wbs_code, current_task_id))
    else:
        df = db_query("SELECT id FROM pms_tasks WHERE wbs_code = %s LIMIT 1;", (wbs_code,))
    return not df.empty

def check_dependency_allowed(task_id, new_status):
    """선행 작업의 상태가 완료 상태인지 검사하여 상태 업데이트 여부를 판별합니다."""
    # 변경하고자 하는 상태가 예정 또는 취소인 경우 의존성 관계는 무관하게 진행 가능
    if new_status in ['예정', '취소']:
        return True, ""
        
    df = db_query("""
        SELECT t.title as task_title, d.title as dep_title, d.status as dep_status 
        FROM pms_tasks t
        JOIN pms_tasks d ON t.dependency_id = d.id
        WHERE t.id = %s;
    """, (task_id,))
    
    if df.empty:
        # 선행 작업이 아예 지정되지 않은 경우 통과
        return True, ""
        
    dep_status = df.iloc[0]['dep_status']
    dep_title = df.iloc[0]['dep_title']
    
    if dep_status != '완료':
        return False, f"선행 필수 작업인 '{dep_title}' (현재 상태: {dep_status})이 아직 완료되지 않아 시작할 수 없습니다."
    
    return True, ""

# ==========================================
# [사이드바 필터 및 관리자 설정]
# ==========================================

st.sidebar.markdown(f"## ⛵ PMS 관제 모니터")
st.sidebar.markdown(f"---")

# 테마 토글 버튼
theme_btn_text = "☀️ 라이트 모드로 변경" if IS_DARK else "🌙 다크 모드로 변경"
st.sidebar.button(theme_btn_text, on_click=toggle_theme, use_container_width=True)
st.sidebar.markdown(f"---")

# DB 필터 데이터 수집
members_df = db_query("SELECT id, name, role FROM pms_members ORDER BY id;")
sprints_df = db_query("SELECT id, name, is_active FROM pms_sprints ORDER BY id;")

# 사이드바 필터링 UI
st.sidebar.markdown("### 🔍 데이터 필터링")
selected_sprint_name = st.sidebar.selectbox(
    "스프린트 선택",
    ["전체 스프린트"] + sprints_df['name'].tolist()
)

selected_member_name = st.sidebar.selectbox(
    "담당 팀원 선택",
    ["전체 팀원"] + members_df['name'].tolist()
)

# 필터 조건에 따른 SQL Where 절 생성
where_clauses = []
query_params = []

if selected_sprint_name != "전체 스프린트":
    sprint_id = sprints_df[sprints_df['name'] == selected_sprint_name].iloc[0]['id']
    where_clauses.append("t.sprint_id = %s")
    query_params.append(int(sprint_id))

if selected_member_name != "전체 팀원":
    member_id = members_df[members_df['name'] == selected_member_name].iloc[0]['id']
    where_clauses.append("t.assignee_id = %s")
    query_params.append(int(member_id))

where_sql = ""
if where_clauses:
    where_sql = "WHERE " + " AND ".join(where_clauses)

# 메인 데이터 조회 (필터링 적용)
tasks_query = f"""
    SELECT t.id, t.title, t.description, t.wbs_code, t.status, t.weight, t.progress, 
           t.start_date, t.end_date, t.parent_id, t.dependency_id,
           m.name as assignee_name, m.role as assignee_role,
           s.name as sprint_name,
           d.title as dependency_title
    FROM pms_tasks t
    LEFT JOIN pms_members m ON t.assignee_id = m.id
    LEFT JOIN pms_sprints s ON t.sprint_id = s.id
    LEFT JOIN pms_tasks d ON t.dependency_id = d.id
    {where_sql}
    ORDER BY t.wbs_code;
"""
tasks_df = db_query(tasks_query, query_params)

# ==========================================
# [메인 콘텐츠 레이아웃]
# ==========================================

st.markdown(f"# 🚢 팀 프로젝트 관제 대시보드")
st.markdown("애자일 마일스톤 관리 및 WBS/갠트 차트 일정 통합 관리 시스템")
st.markdown("---")

# 1. 상단 대시보드 지표 연산 및 렌더링
if not tasks_df.empty:
    # 전체 진척율 계산 (가중치 적용 평균: sum(progress * weight) / sum(weight))
    total_weight = tasks_df['weight'].sum()
    if total_weight > 0:
        total_progress = int((tasks_df['progress'] * tasks_df['weight']).sum() / total_weight)
    else:
        total_progress = 0
        
    done_tasks = tasks_df[tasks_df['status'] == '완료'].shape[0]
    total_tasks = tasks_df.shape[0]
else:
    total_progress = 0
    done_tasks = 0
    total_tasks = 0

# 활성 스프린트 정보 가져오기
active_sprint = sprints_df[sprints_df['is_active'] == True]
active_sprint_text = active_sprint.iloc[0]['name'] if not active_sprint.empty else "활성화된 스프린트 없음"

# [수정] 프로젝트 타임라인 계산 로직 (시작일, 종료일 고정)
today = datetime.date.today()
project_start = datetime.date(today.year, 6, 1)
project_end = datetime.date(today.year, 7, 31)

# 기간 계산 (방어 코드 포함 - Early Return 개념 적용)
total_days = max(1, (project_end - project_start).days + 1)
if today < project_start:
    passed_days = 0
elif today > project_end:
    passed_days = total_days
else:
    passed_days = (today - project_start).days + 1
    
time_progress = int((passed_days / total_days) * 100)
is_ahead = total_progress >= time_progress
status_msg = "🚀 <b>순조로움:</b> 계획된 시간보다 실제 업무가 더 빠르게 진행되고 있습니다!" if is_ahead else "⚠️ <b>주의 요망:</b> 시간 경과 대비 실제 업무 진행이 지연되고 있습니다. 일정을 점검해 주세요."

# 타임라인 종합 현황판 렌더링
st.markdown(f"""
<div class="pms-card">
    <div class="pms-card-label" style="font-size:1.05rem;">⏱️ 종합 타임라인 분석 (시간 경과 vs 실제 업무 진척)</div>
    <div style="margin-top: 1.25rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; color: {TEXT_MUTED}; font-weight: 500;">
        <div style="flex: 1; text-align: left;">🏁 시작일<br><b style="color:{TEXT_COLOR};">{project_start.strftime('%Y-%m-%d')}</b></div>
        <div style="flex: 1; text-align: center; color: {'#fb923c' if IS_DARK else ACCENT_ORANGE}; font-weight: bold; background-color: rgba(249, 115, 22, 0.1); padding: 0.5rem 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
            📍 오늘: {today.strftime('%Y-%m-%d')}<br>
            <span style="font-size:0.85rem;">(진행 {passed_days}일차 / 총 {total_days}일)</span>
        </div>
        <div style="flex: 1; text-align: right;">🎯 종료일<br><b style="color:{TEXT_COLOR};">{project_end.strftime('%Y-%m-%d')}</b></div>
    </div>
    <div style="margin: 1.75rem 0 1rem 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.4rem;">
            <span>⏳ 시간 경과율</span>
            <span style="font-weight: bold;">{time_progress}%</span>
        </div>
        <div style="background-color: {BORDER_COLOR}; border-radius: 6px; width: 100%; height: 16px; overflow: hidden;">
            <div style="background-color: {TEXT_MUTED}; width: {time_progress}%; height: 100%; border-radius: 6px; transition: width 0.5s ease-in-out;"></div>
        </div>
    </div>
    <div style="margin: 1rem 0 1rem 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.4rem;">
            <span>🔥 실제 업무 진척률</span>
            <span style="font-weight: bold; color: {ACCENT_BLUE};">{total_progress}%</span>
        </div>
        <div style="background-color: {BORDER_COLOR}; border-radius: 6px; width: 100%; height: 16px; overflow: hidden;">
            <div style="background-color: {ACCENT_BLUE}; width: {total_progress}%; height: 100%; border-radius: 6px; transition: width 0.5s ease-in-out;"></div>
        </div>
    </div>
    <div style="margin-top: 1.25rem; font-size: 0.95rem; padding: 1rem; background-color: {'#18181b' if IS_DARK else '#f8fafc'}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; border-left: 4px solid {ACCENT_GREEN if is_ahead else ACCENT_ORANGE};">
        {status_msg}
    </div>
</div>
""", unsafe_allow_html=True)

# 대시보드 요약 지표 (3단 가로 배치)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="pms-card">
        <div class="pms-card-label">⚓ 전체 진척율 요약</div>
        <div class="pms-card-value" style="color: {ACCENT_BLUE};">{total_progress}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="pms-card">
        <div class="pms-card-label">🔥 현재 활성 스프린트</div>
        <div class="pms-card-value" style="font-size: 1.15rem; margin-top:0.75rem;">{active_sprint_text}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="pms-card">
        <div class="pms-card-label">✅ 완료된 작업 / 총 작업</div>
        <div class="pms-card-value">{done_tasks} / {total_tasks}개</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# [핵심 기능 탭 구조]
# ==========================================

tab_gantt, tab_kanban, tab_members, tab_crud = st.tabs([
    "📊 WBS & 갠트 차트 (Gantt Chart)", 
    "📋 애자일 칸반 보드 (Kanban Board)", 
    "👥 팀원 진척 상황", 
    "⚙️ 작업 관리 (CRUD)"
])

# ------------------------------------------
# [탭 1: WBS & 갠트 차트]
# ------------------------------------------
with tab_gantt:
    st.subheader("🗓️ Gantt Chart 타임라인")
    
    if not tasks_df.empty:
        # Plotly Gantt Timeline 그리기
        # 시작일과 종료일이 Timestamp로 제대로 매핑될 수 있도록 포맷 맞춤
        gantt_data = tasks_df.copy()
        gantt_data['start_date'] = pd.to_datetime(gantt_data['start_date'])
        gantt_data['end_date'] = pd.to_datetime(gantt_data['end_date'])
        
        # 상태에 따른 고유 색상 맵핑
        status_colors = {
            '예정': '#94a3b8',   # 연회색
            '진행중': '#2563eb', # 파란색
            '완료': '#22c55e',   # 초록색
            '취소': '#ef4444'    # 빨간색
        }
        
        fig = px.timeline(
            gantt_data,
            x_start="start_date",
            x_end="end_date",
            y="title",
            color="status",
            color_discrete_map=status_colors,
            hover_data={
                "wbs_code": True,
                "assignee_name": True,
                "progress": ":.0f%",
                "dependency_title": True,
                "start_date": "|%Y-%m-%d",
                "end_date": "|%Y-%m-%d"
            },
            title="마일스톤 및 작업 일정 현황"
        )
        
        # 갠트 차트 레이아웃 스타일 개선
        fig.update_yaxes(autorange="reversed")  # 위에서 아래로 정렬 순서 유지
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=TEXT_COLOR,
            xaxis=dict(gridcolor=BORDER_COLOR),
            yaxis=dict(gridcolor=BORDER_COLOR),
            legend_title_text="상태",
            height=400
        )
        
        # [확인용 출력] 간트 차트에 세로 가이드라인으로 표시될 오늘 날짜 정보 출력
        today_date = datetime.date.today()
        print(f"[갠트 차트] 오늘 날짜인 '{today_date}' 기준으로 수직 가이드라인(오늘선)을 추가합니다.")
        
        # 오늘 날짜 위치에 주황색 세로 점선 가이드라인 및 라벨을 추가합니다.
        fig.add_vline(
            x=today_date.strftime("%Y-%m-%d"),
            line_width=2,
            line_dash="dash",
            line_color="#f97316",  # 주황색 강조색 사용
            annotation_text="오늘 (Today)",
            annotation_position="top left",
            annotation_font=dict(color="#f97316", size=11, family="Inter")
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("조회 조건에 일치하는 작업 내역이 없습니다.")
        
    st.markdown("---")
    st.subheader("📂 WBS (업무 구조 분할 정의)")
    
    if not tasks_df.empty:
        # WBS 구조 테이블을 계층적으로 정렬해서 렌더링
        wbs_view = tasks_df.copy()
        
        # 계층 깊이 구하기 (WBS 코드가 '1.1.2' 이면 . 이 2개 있으므로 깊이는 2)
        def get_depth_indent(wbs):
            dots = wbs.count('.')
            if dots == 0:
                return f"📁 **{wbs}**"
            elif dots == 1:
                return f" 📄 **{wbs}**"
            else:
                return f"  └ 🛠️ {wbs}"
                
        wbs_view['계층 코드'] = wbs_view['wbs_code'].apply(get_depth_indent)
        
        # 화면 표기용 컬럼 가공
        wbs_view_table = wbs_view[[
            '계층 코드', 'title', 'assignee_name', 'sprint_name', 
            'start_date', 'end_date', 'weight', 'progress', 'status', 'dependency_title'
        ]].rename(columns={
            'title': '작업명',
            'assignee_name': '담당자',
            'sprint_name': '스프린트',
            'start_date': '시작일',
            'end_date': '종료일',
            'weight': '가중치',
            'progress': '진척도 (%)',
            'status': '상태',
            'dependency_title': '선행 필수 작업'
        })
        
        st.dataframe(wbs_view_table, use_container_width=True, hide_index=True)
    else:
        st.info("WBS 테이블을 구성할 데이터가 비어 있습니다.")

# ------------------------------------------
# [탭 2: 애자일 칸반 보드]
# ------------------------------------------
with tab_kanban:
    st.subheader("🏃 애자일 칸반 보드 (Kanban Board)")
    st.caption("작업 카드를 아래에서 확인하고, 하단의 상태 변경 퀵 메뉴를 통해 일정을 즉시 업데이트할 수 있습니다.")
    
    # 4열 칸반 구조 렌더링
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)
    statuses = ['예정', '진행중', '완료', '취소']
    column_mappings = {
        '예정': (k_col1, "📌 예정 (To-Do)"),
        '진행중': (k_col2, "⚡ 진행 중 (In Progress)"),
        '완료': (k_col3, "✅ 완료 (Done)"),
        '취소': (k_col4, "🚫 취소 (Cancelled)")
    }
    
    for s_name in statuses:
        col_ui, col_title = column_mappings[s_name]
        with col_ui:
            # 해당 상태에 속한 태스크 필터링
            sub_tasks = tasks_df[tasks_df['status'] == s_name] if not tasks_df.empty else pd.DataFrame()
            
            # [확인용 출력] 어떤 칸반 열에 몇 개의 작업이 들어가는지 터미널에 로깅
            print(f"[칸반 렌더링] 상태: {s_name} | 작업 개수: {len(sub_tasks)}개")
            
            # HTML 구조가 깨지지 않고 카드들이 열 내부에 위치하도록 하나의 문자열로 조립하여 출력
            kanban_html = f'<div class="kanban-col"><div class="kanban-header">{col_title}</div>'
            
            if not sub_tasks.empty:
                for idx, row in sub_tasks.iterrows():
                    dep_text = f"<br>⚠️ 선행 작업 필요: {row['dependency_title']}" if row['dependency_title'] else ""
                    card_html = f"""
                        <div class="kanban-card">
                            <div class="kanban-card-title">[{row['wbs_code']}] {row['title']}</div>
                            <div class="kanban-card-meta">
                                👤 {row['assignee_name'] or '미배정'} ({row['assignee_role'] or '역할 없음'})<br>
                                📅 {row['start_date']} ~ {row['end_date']}<br>
                                📊 진척도: <b>{row['progress']}%</b> (가중치: {row['weight']})
                                {dep_text}
                            </div>
                        </div>
                    """
                    # 각 줄의 앞뒤 공백을 제거하여 마크다운이 코드 블록으로 오인하는 현상을 방지합니다.
                    kanban_html += "\n".join([line.strip() for line in card_html.split("\n") if line.strip()])
            else:
                kanban_html += f'<div style="color:{TEXT_MUTED}; font-size:0.8rem; text-align:center; padding: 2rem 0;">작업 없음</div>'
            
            kanban_html += '</div>'
            
            # 하나의 st.markdown으로 모든 HTML 구조를 한번에 주입
            st.markdown(kanban_html, unsafe_allow_html=True)
            
    st.markdown("---")
    st.subheader("⚡ 칸반 카드 상태 퀵 업데이트")
    
    # 퀵 업데이트 폼
    if not tasks_df.empty:
        col_select_task, col_select_status, col_btn = st.columns([3, 2, 1])
        
        with col_select_task:
            task_options = {f"[{row['wbs_code']}] {row['title']}": row['id'] for idx, row in tasks_df.iterrows()}
            selected_task_label = st.selectbox("업데이트할 작업 선택", list(task_options.keys()), key="kanban_quick_task")
            selected_task_id = task_options[selected_task_label]
            
        with col_select_status:
            current_status = tasks_df[tasks_df['id'] == selected_task_id].iloc[0]['status']
            status_index = statuses.index(current_status)
            target_status = st.selectbox("변경할 상태", statuses, index=status_index, key="kanban_quick_status")
            
        with col_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("상태 저장 💾", use_container_width=True, key="kanban_quick_save"):
                # 입구에서 검사 (의존성 체크)
                allowed, msg = check_dependency_allowed(selected_task_id, target_status)
                if not allowed:
                    st.error(msg)
                else:
                    # 완료로 갈 경우 자동으로 progress 100% 처리, 예정/취소로 가면 0% 처리
                    prog_update_sql = ""
                    if target_status == '완료':
                        prog_update_sql = ", progress = 100"
                    elif target_status in ['예정', '취소']:
                        prog_update_sql = ", progress = 0"
                        
                    success = db_execute(f"""
                        UPDATE pms_tasks 
                        SET status = %s {prog_update_sql}
                        WHERE id = %s;
                    """, (target_status, int(selected_task_id)))
                    
                    if success:
                        st.success("상태 변경이 성공적으로 저장되었습니다.")
                        st.rerun()
    else:
        st.info("업데이트할 작업이 없습니다.")

# ------------------------------------------
# [탭 3: 팀원 진척 상황]
# ------------------------------------------
with tab_members:
    st.subheader("👥 프로젝트 참여 팀원 역할 및 일정")
    st.dataframe(members_df.rename(columns={
        'name': '팀원명',
        'role': '배정 직무',
        'start_date': '참여 시작일',
        'end_date': '참여 종료일'
    }), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("📊 팀원별 누적 업무 진척 상황 (가중치 평균)")
    
    # 팀원별 평균 진척율 계산
    # 모든 태스크 목록을 읽어옵니다. (필터 해제된 순수 전체 통계용)
    all_tasks = db_query("""
        SELECT t.assignee_id, t.weight, t.progress, m.name as member_name 
        FROM pms_tasks t
        JOIN pms_members m ON t.assignee_id = m.id;
    """)
    
    if not all_tasks.empty:
        # 그룹화 연산
        all_tasks['weighted_prog'] = all_tasks['progress'] * all_tasks['weight']
        grouped = all_tasks.groupby('member_name').agg(
            total_weighted_prog=('weighted_prog', 'sum'),
            total_weight=('weight', 'sum')
        ).reset_index()
        
        grouped['average_progress'] = (grouped['total_weighted_prog'] / grouped['total_weight']).round(1)
        
        # Plotly 가로 막대 그래프 그리기
        fig_member = px.bar(
            grouped,
            x="average_progress",
            y="member_name",
            orientation='h',
            text="average_progress",
            labels={'average_progress': '진척율 (%)', 'member_name': '팀원명'},
            color="average_progress",
            color_continuous_scale=px.colors.sequential.Viridis
        )
        
        fig_member.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=TEXT_COLOR,
            xaxis=dict(gridcolor=BORDER_COLOR, range=[0, 100]),
            yaxis=dict(gridcolor=BORDER_COLOR),
            height=300
        )
        st.plotly_chart(fig_member, use_container_width=True)
    else:
        st.info("등록된 작업이 없어 팀원별 통계를 낼 수 없습니다.")

# ------------------------------------------
# [탭 4: 작업 관리 (CRUD)]
# ------------------------------------------
with tab_crud:
    st.subheader("⚙️ 작업 등록 / 수정 / 삭제 관리 패널")
    
    crud_mode = st.radio("수행할 작업을 선택하세요", ["작업 추가 (+)", "작업 수정 (✏️)", "작업 삭제 (🗑️)"], horizontal=True)
    st.markdown("---")
    
    # DB 최신 옵션 목록
    member_opts = {row['name']: row['id'] for idx, row in members_df.iterrows()}
    sprint_opts = {row['name']: row['id'] for idx, row in sprints_df.iterrows()}
    
    # 4.1 작업 추가 폼
    if crud_mode == "작업 추가 (+)":
        st.markdown("#### ➕ 새로운 WBS 작업 등록")
        
        # 전체 등록된 태스크 목록 (의존성 설정을 위함)
        all_tasks_raw = db_query("SELECT id, title, wbs_code FROM pms_tasks ORDER BY wbs_code;")
        task_opts = {"없음 (선행 작업 없음)": None}
        for idx, row in all_tasks_raw.iterrows():
            task_opts[f"[{row['wbs_code']}] {row['title']}"] = row['id']
            
        with st.form("add_task_form"):
            c_title = st.text_input("작업명 (필수)")
            c_wbs = st.text_input("WBS 코드 (필수, 예: 1.4, 2.1.3)")
            c_desc = st.text_area("작업 상세 설명")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                c_assignee = st.selectbox("담당 팀원 배정", list(member_opts.keys()))
            with col_b:
                c_sprint = st.selectbox("소속 스프린트", list(sprint_opts.keys()))
            with col_c:
                c_dep = st.selectbox("선행 필수 작업(의존성)", list(task_opts.keys()))
                
            col_d, col_e, col_f, col_g = st.columns(4)
            with col_d:
                c_start = st.date_input("시작일", datetime.date.today())
            with col_e:
                c_end = st.date_input("종료일", datetime.date.today() + datetime.timedelta(days=7))
            with col_f:
                c_weight = st.number_input("작업 가중치 (1~5)", min_value=1, max_value=5, value=1)
            with col_g:
                c_progress = st.slider("진척율 (%)", 0, 100, 0)
                
            c_status = st.selectbox("초기 상태", ["예정", "진행중", "완료", "취소"])
            
            submit_btn = st.form_submit_button("작업 등록하기 🚀")
            
            if submit_btn:
                # 입구에서 검사 (Early Return) - 필수 항목 확인
                if not c_title.strip():
                    st.error("오류: 작업명을 입력해 주세요.")
                elif not c_wbs.strip():
                    st.error("오류: WBS 코드를 입력해 주세요.")
                elif c_start > c_end:
                    st.error("오류: 시작일은 종료일보다 이전 날짜여야 합니다.")
                elif is_wbs_code_duplicate(c_wbs):
                    st.error(f"오류: WBS 코드 '{c_wbs}'는 이미 존재합니다. 다른 코드를 사용해주세요.")
                else:
                    # 의존성 검사
                    dep_id = task_opts[c_dep]
                    allowed, msg = check_dependency_allowed(dep_id, c_status) if dep_id else (True, "")
                    if not allowed:
                        st.error(f"의존성 오류: {msg}")
                    else:
                        success = db_execute("""
                            INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """, (c_title, c_desc, c_wbs, c_status, int(c_weight), int(member_opts[c_assignee]), int(sprint_opts[c_sprint]), c_start, c_end, int(c_progress), dep_id))
                        
                        if success:
                            st.success(f"새 작업 '{c_title}'이 성공적으로 WBS에 추가되었습니다!")
                            st.rerun()

    # 4.2 작업 수정 폼
    elif crud_mode == "작업 수정 (✏️)":
        st.markdown("#### ✏️ 기존 WBS 작업 정보 수정")
        
        if not tasks_df.empty:
            # 수정할 대상 설정
            task_sel_opts = {f"[{row['wbs_code']}] {row['title']}": row['id'] for idx, row in tasks_df.iterrows()}
            selected_task_label = st.selectbox("수정할 작업을 선택하세요", list(task_sel_opts.keys()))
            selected_id = task_sel_opts[selected_task_label]
            
            # 현재 데이터 조회
            curr_task = tasks_df[tasks_df['id'] == selected_id].iloc[0]
            
            # 의존성 목록 가공 (본인 제외)
            all_tasks_raw = db_query("SELECT id, title, wbs_code FROM pms_tasks WHERE id != %s ORDER BY wbs_code;", (int(selected_id),))
            task_opts = {"없음 (선행 작업 없음)": None}
            for idx, row in all_tasks_raw.iterrows():
                task_opts[f"[{row['wbs_code']}] {row['title']}"] = row['id']
                
            # 기본 선택값 세팅
            def_member_name = curr_task['assignee_name'] if curr_task['assignee_name'] in member_opts else list(member_opts.keys())[0]
            def_sprint_name = curr_task['sprint_name'] if curr_task['sprint_name'] in sprint_opts else list(sprint_opts.keys())[0]
            
            def_dep_label = "없음 (선행 작업 없음)"
            if curr_task['dependency_id']:
                for k, v in task_opts.items():
                    if v == curr_task['dependency_id']:
                        def_dep_label = k
                        break
                        
            with st.form("edit_task_form"):
                u_title = st.text_input("작업명", value=curr_task['title'])
                u_wbs = st.text_input("WBS 코드", value=curr_task['wbs_code'])
                u_desc = st.text_area("작업 상세 설명", value=curr_task['description'] or "")
                
                col_ua, col_ub, col_uc = st.columns(3)
                with col_ua:
                    u_assignee = st.selectbox("담당 팀원 배정", list(member_opts.keys()), index=list(member_opts.keys()).index(def_member_name))
                with col_ub:
                    u_sprint = st.selectbox("소속 스프린트", list(sprint_opts.keys()), index=list(sprint_opts.keys()).index(def_sprint_name))
                with col_uc:
                    u_dep = st.selectbox("선행 필수 작업(의존성)", list(task_opts.keys()), index=list(task_opts.keys()).index(def_dep_label) if def_dep_label in task_opts else 0)
                    
                col_ud, col_ue, col_uf, col_ug = st.columns(4)
                # 날짜 파싱 안전 처리
                start_dt = curr_task['start_date']
                end_dt = curr_task['end_date']
                if isinstance(start_dt, str):
                    start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d").date()
                if isinstance(end_dt, str):
                    end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d").date()
                    
                with col_ud:
                    u_start = st.date_input("시작일", value=start_dt)
                with col_ue:
                    u_end = st.date_input("종료일", value=end_dt)
                with col_uf:
                    u_weight = st.number_input("작업 가중치 (1~5)", min_value=1, max_value=5, value=int(curr_task['weight']))
                with col_ug:
                    u_progress = st.slider("진척율 (%)", 0, 100, value=int(curr_task['progress']))
                    
                u_status = st.selectbox("상태", ["예정", "진행중", "완료", "취소"], index=["예정", "진행중", "완료", "취소"].index(curr_task['status']))
                
                update_btn = st.form_submit_button("정보 업데이트 ✏️")
                
                if update_btn:
                    # 입구에서 검사 (Early Return)
                    if not u_title.strip():
                        st.error("오류: 작업명은 비워둘 수 없습니다.")
                    elif not u_wbs.strip():
                        st.error("오류: WBS 코드는 비워둘 수 없습니다.")
                    elif u_start > u_end:
                        st.error("오류: 시작일이 종료일보다 이전 날짜여야 합니다.")
                    elif is_wbs_code_duplicate(u_wbs, selected_id):
                        st.error(f"오류: WBS 코드 '{u_wbs}'는 이미 다른 작업에서 사용 중입니다.")
                    else:
                        # 의존성 검증
                        dep_id = task_opts[u_dep]
                        allowed, msg = check_dependency_allowed(dep_id, u_status) if dep_id else (True, "")
                        if not allowed:
                            st.error(f"의존성 오류: {msg}")
                        else:
                            success = db_execute("""
                                UPDATE pms_tasks
                                SET title = %s, description = %s, wbs_code = %s, status = %s, 
                                    weight = %s, assignee_id = %s, sprint_id = %s, 
                                    start_date = %s, end_date = %s, progress = %s, dependency_id = %s
                                WHERE id = %s;
                            """, (u_title, u_desc, u_wbs, u_status, int(u_weight), int(member_opts[u_assignee]), int(sprint_opts[u_sprint]), u_start, u_end, int(u_progress), dep_id, int(selected_id)))
                            
                            if success:
                                st.success("작업 정보가 성공적으로 수정되었습니다!")
                                st.rerun()
        else:
            st.info("수정할 작업 데이터가 존재하지 않습니다.")

    # 4.3 작업 삭제
    elif crud_mode == "작업 삭제 (🗑️)":
        st.markdown("#### 🗑️ 기존 WBS 작업 영구 삭제")
        
        if not tasks_df.empty:
            task_del_opts = {f"[{row['wbs_code']}] {row['title']}": row['id'] for idx, row in tasks_df.iterrows()}
            selected_del_label = st.selectbox("삭제할 작업을 선택하세요", list(task_del_opts.keys()))
            selected_del_id = task_del_opts[selected_del_label]
            
            # 혹시 해당 태스크를 선행 작업으로 참조하고 있는 다른 태스크가 있는지 검사
            ref_tasks = db_query("SELECT id, title, wbs_code FROM pms_tasks WHERE dependency_id = %s;", (int(selected_del_id),))
            
            warning_msg = "이 작업을 정말로 삭제하시겠습니까? 삭제 후에는 복구할 수 없습니다."
            if not ref_tasks.empty:
                ref_titles = ", ".join([f"[{r['wbs_code']}] {r['title']}" for idx, r in ref_tasks.iterrows()])
                st.warning(f"⚠️ 경고: 이 작업은 다음 작업의 선행 필수 작업으로 참조되고 있습니다: {ref_titles}. 이 작업을 삭제하면 후행 작업들의 의존성도 함께 끊어지게 됩니다.")
            
            confirm_del = st.checkbox("예, 삭제를 확정하겠습니다.")
            
            if st.button("작업 영구 삭제 🗑️", type="primary"):
                # 입구에서 검사 (Early Return)
                if not confirm_del:
                    st.error("삭제 확정 체크박스에 체크해 주셔야 삭제 처리가 가능합니다.")
                else:
                    # 먼저 해당 태스크를 참조하는 후행 태스크들의 dependency_id를 NULL로 설정
                    if not ref_tasks.empty:
                        db_execute("UPDATE pms_tasks SET dependency_id = NULL WHERE dependency_id = %s;", (int(selected_del_id),))
                        
                    success = db_execute("DELETE FROM pms_tasks WHERE id = %s;", (int(selected_del_id),))
                    if success:
                        st.success("작업이 성공적으로 영구 삭제되었습니다.")
                        st.rerun()
        else:
            st.info("삭제할 작업 데이터가 존재하지 않습니다.")
