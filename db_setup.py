# -*- coding: utf-8 -*-
"""
팀 프로젝트 진행상황 관리 시스템(PMS) - Neon DB 초기 테이블 설정 및 더미 데이터 주입 스크립트
다중 프로젝트 스키마 추가 버전
작성자: Antigravity AI
"""

import os
import psycopg2
import datetime
from dotenv import load_dotenv

# 1. 입구에서 검사 (Early Return) - 환경 변수 로드 상태 확인
env_path = '.env.local'
if not os.path.exists(env_path):
    print(f"[오류] {env_path} 파일이 존재하지 않습니다. 환경 변수 설정을 먼저 해주세요.")
    exit(1)

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[오류] DATABASE_URL 환경 변수가 설정되지 않았습니다. .env.local 파일을 확인해주세요.")
    exit(1)

print("[안내] Neon DB에 연결을 시도합니다...")

try:
    # 2. 데이터베이스 연결 생성
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    print("[성공] Neon DB 연결에 성공하였습니다.")

    # 3. 기존 테이블 제거 (순서 중요: 외래키 의존성 역순)
    print("[작업] 기존 PMS 관련 테이블이 있다면 초기화(DROP)합니다...")
    cursor.execute("DROP TABLE IF EXISTS pms_tasks CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS pms_sprints CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS pms_members CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS pms_projects CASCADE;")
    print("[성공] 기존 테이블 제거 완료.")

    # 4. 테이블 생성
    # 4.1. 프로젝트 테이블 (pms_projects)
    print("[작업] pms_projects 테이블을 생성합니다...")
    cursor.execute("""
        CREATE TABLE pms_projects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            client VARCHAR(255),
            description TEXT
        );
    """)

    # 4.2. 팀원 테이블 (pms_members)
    print("[작업] pms_members 테이블을 생성합니다...")
    cursor.execute("""
        CREATE TABLE pms_members (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            role VARCHAR(100) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL
        );
    """)
    
    # 4.3. 스프린트 테이블 (pms_sprints)
    print("[작업] pms_sprints 테이블을 생성합니다...")
    cursor.execute("""
        CREATE TABLE pms_sprints (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_active BOOLEAN DEFAULT FALSE,
            project_id INTEGER REFERENCES pms_projects(id) ON DELETE CASCADE
        );
    """)

    # 4.4. 작업 테이블 (pms_tasks)
    print("[작업] pms_tasks 테이블을 생성합니다...")
    cursor.execute("""
        CREATE TABLE pms_tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            wbs_code VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL CHECK (status IN ('예정', '진행중', '완료', '취소')),
            weight INTEGER DEFAULT 1,
            assignee_id INTEGER REFERENCES pms_members(id) ON DELETE SET NULL,
            sprint_id INTEGER REFERENCES pms_sprints(id) ON DELETE SET NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
            parent_id INTEGER REFERENCES pms_tasks(id) ON DELETE SET NULL,
            dependency_id INTEGER REFERENCES pms_tasks(id) ON DELETE SET NULL
        );
    """)
    print("[성공] 모든 테이블 생성 완료.")

    # 5. 초기 데이터 주입 (Insert)
    
    # 5.1. 프로젝트 초기 데이터 주입
    print("[작업] 프로젝트(pms_projects) 초기 데이터를 등록합니다...")
    cursor.execute("""
        INSERT INTO pms_projects (name, start_date, end_date, client, description)
        VALUES (%s, %s, %s, %s, %s) RETURNING id;
    """, ("팀 프로젝트 관리 시스템(PMS) 구축", "2026-06-01", "2026-07-31", "Antigravity Corp", "대시보드 및 WBS 갠트차트 개발 프로젝트"))
    project_id = cursor.fetchone()[0]
    print(f"[성공] 기본 프로젝트 등록 완료. (ID: {project_id})")

    # 5.2. 팀원 데이터 주입
    print("[작업] 팀원(pms_members) 초기 데이터를 등록합니다...")
    members = [
        ("팀원1", "기획자 & 테스터", "2026-06-01", "2026-08-31"),
        ("팀원2", "백엔드 개발자", "2026-06-01", "2026-08-31"),
        ("팀원3", "프론트엔드 개발자", "2026-06-01", "2026-08-31"),
        ("팀원4", "API 개발자", "2026-06-01", "2026-08-31"),
        ("팀원5", "디자인 및 퍼블리셔", "2026-06-01", "2026-08-31")
    ]
    for m in members:
        cursor.execute("""
            INSERT INTO pms_members (name, role, start_date, end_date) 
            VALUES (%s, %s, %s, %s);
        """, m)
    print("[성공] 팀원 데이터 등록 완료.")

    # 5.3. 스프린트 데이터 주입 (요청에 따라 1~7단계로 재구성 및 프로젝트 연결)
    print("[작업] 스프린트(pms_sprints) 초기 데이터를 등록합니다...")
    sprints = [
        ("스프린트 1: 프로젝트관리", "2026-06-01", "2026-06-07", False, project_id),
        ("스프린트 2: 기획 및 화면설계", "2026-06-08", "2026-06-15", False, project_id),
        ("스프린트 3: UI 디자인", "2026-06-16", "2026-06-22", False, project_id),
        ("스프린트 4: 프론트개발", "2026-06-23", "2026-07-07", True, project_id), # 오늘(6/26) 속한 스프린트 활성화
        ("스프린트 5: 백엔드개발", "2026-06-23", "2026-07-07", False, project_id),
        ("스프린트 6: API개발 및 프론트연동", "2026-07-08", "2026-07-22", False, project_id),
        ("스프린트 7: QA테스트", "2026-07-23", "2026-07-31", False, project_id)
    ]
    for s in sprints:
        cursor.execute("""
            INSERT INTO pms_sprints (name, start_date, end_date, is_active, project_id) 
            VALUES (%s, %s, %s, %s, %s);
        """, s)
    print("[성공] 스프린트 데이터 등록 완료.")

    # 5.4. 작업 데이터 주입 (계층 구조 및 의존성을 위해 순차 등록)
    print("[작업] 작업(pms_tasks) 초기 데이터를 등록합니다...")
    
    # 팀원 ID 매핑 정보 조회
    cursor.execute("SELECT id, name FROM pms_members;")
    member_map = {row[1]: row[0] for row in cursor.fetchall()}
    
    # 스프린트 ID 매핑 정보 조회
    cursor.execute("SELECT id, name FROM pms_sprints WHERE project_id = %s;", (project_id,))
    sprint_map = {}
    for row in cursor.fetchall():
        if "스프린트 1" in row[1]:
            sprint_map[1] = row[0]
        elif "스프린트 2" in row[1]:
            sprint_map[2] = row[0]
        elif "스프린트 3" in row[1]:
            sprint_map[3] = row[0]
        elif "스프린트 4" in row[1]:
            sprint_map[4] = row[0]
        elif "스프린트 5" in row[1]:
            sprint_map[5] = row[0]
        elif "스프린트 6" in row[1]:
            sprint_map[6] = row[0]
        elif "스프린트 7" in row[1]:
            sprint_map[7] = row[0]

    # [스프린트 1 업무 추가]
    # 1.0 프로젝트 전체 일정 및 자원 관리
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("전체 프로젝트 일정 및 자원 관리", "프로젝트 일정 조율 및 작업 분배 관리", "1.0", "완료", 3, member_map["팀원1"], sprint_map[1], "2026-06-01", "2026-06-07", 100))
    t1_0_id = cursor.fetchone()[0]

    # [스프린트 2 업무 추가]
    # 1.1 요구사항 정의 및 화면 설계 (팀원1)
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, parent_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("요구사항 정의 및 화면 설계", "프로젝트의 전반적인 기능 정의서와 와이어프레임 설계", "1.1", "완료", 3, member_map["팀원1"], sprint_map[2], "2026-06-08", "2026-06-15", 100, t1_0_id))
    t1_1_id = cursor.fetchone()[0]

    # [스프린트 5 업무 추가 (기획 완료 후 DB 및 API 기획)]
    # 1.2 DB 스키마 설계 및 생성 (팀원2)
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, parent_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("DB 스키마 설계 및 테이블 생성", "Neon DB를 연동하기 위한 관계형 테이블 설계", "1.2", "완료", 3, member_map["팀원2"], sprint_map[5], "2026-06-08", "2026-06-12", 100, t1_1_id))
    t1_2_id = cursor.fetchone()[0]

    # 1.3 API 명세서 작성 (팀원4)
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, parent_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("API 명세서 및 Mock 데이터 생성", "백엔드와 프론트엔드가 공유할 REST API 설계 문서화", "1.3", "완료", 2, member_map["팀원4"], sprint_map[5], "2026-06-10", "2026-06-15", 100, t1_1_id))
    t1_3_id = cursor.fetchone()[0]

    # [스프린트 3 업무 추가]
    # 2.1 UI/UX 디자인 시안 제작 (팀원5)
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("UI/UX 디자인 시안 제작", "피그마를 통한 대시보드 및 상세 페이지 비주얼 가이드 디자인", "2.1", "진행중", 3, member_map["팀원5"], sprint_map[3], "2026-06-16", "2026-06-22", 80))
    t2_1_id = cursor.fetchone()[0]

    # 2.2 퍼블리싱 및 컴포넌트 개발 (팀원5) - 의존성: 2.1 디자인 완료 후 가능
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("웹 퍼블리싱 및 CSS 구축", "HTML 마크업 및 CSS 스타일 가이드 구현", "2.2", "예정", 2, member_map["팀원5"], sprint_map[3], "2026-06-23", "2026-06-30", 0, t2_1_id))
    t2_2_id = cursor.fetchone()[0]

    # [스프린트 5 업무 추가]
    # 2.3 백엔드 CRUD API 구현 (팀원2) - 의존성: 1.3 API 명세서 완료 후 가능
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("백엔드 CRUD API 개발", "Neon DB와 연동하여 작업 추가/수정/삭제를 처리하는 API 작성", "2.3", "진행중", 4, member_map["팀원2"], sprint_map[5], "2026-06-16", "2026-06-25", 90, t1_3_id))
    t2_3_id = cursor.fetchone()[0]

    # [스프린트 4 업무 추가]
    # 2.4 프론트엔드 기본 레이아웃 구현 (팀원3) - 의존성: 1.1 기획 설계 완료 후 가능
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("프론트엔드 기본 레이아웃 구현", "사이드바, 네비게이션바 및 페이지 컨테이너 뼈대 개발", "2.4", "진행중", 3, member_map["팀원3"], sprint_map[4], "2026-06-18", "2026-06-26", 50, t1_1_id))
    t2_4_id = cursor.fetchone()[0]

    # [스프린트 6 업무 추가]
    # 3.1 API 연동 및 상태 관리 개발 (팀원3) - 의존성: 2.3 백엔드 API 완료 후 가능
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("API 연동 및 동적 차트 개발", "프론트엔드와 백엔드 API 연동 및 실시간 Plotly 그래프 렌더링", "3.1", "예정", 4, member_map["팀원3"], sprint_map[6], "2026-07-01", "2026-07-10", 0, t2_3_id))
    t3_1_id = cursor.fetchone()[0]

    # [스프린트 7 업무 추가]
    # 3.2 통합 테스트 및 QA (팀원1) - 의존성: 3.1 연동 완료 후 가능
    cursor.execute("""
        INSERT INTO pms_tasks (title, description, wbs_code, status, weight, assignee_id, sprint_id, start_date, end_date, progress, dependency_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, ("통합 테스트 및 버그 수정 QA", "최종 빌드 후 기능별 단위 테스트 및 성능 QA 수행", "3.2", "예정", 3, member_map["팀원1"], sprint_map[7], "2026-07-11", "2026-07-15", 0, t3_1_id))
    t3_2_id = cursor.fetchone()[0]

    print("[성공] 초기 작업 데이터(pms_tasks) 주입 완료.")
    
    # 연결 리소스 반환
    cursor.close()
    conn.close()
    print("[성공] 모든 DB 초기 설정 작업이 안전하게 종료되었습니다.")

except Exception as e:
    print(f"[오류] 데이터베이스 초기화 중 예외가 발생했습니다: {e}")
