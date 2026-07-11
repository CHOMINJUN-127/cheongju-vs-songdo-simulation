import os
import sys

# ==========================================
# 0. [핵심] streamlit run 명령어가 필요 없도록 자동 실행 로직 삽입
# ==========================================
if __name__ == "__main__":
    if not hasattr(sys, '_meipass') and "STREAMLIT_RUN_ORIGIN" not in os.environ:
        from streamlit.web import cli as stcli
        os.environ["STREAMLIT_RUN_ORIGIN"] = "1"
        sys.argv = ["streamlit", "run", __file__]
        sys.exit(stcli.main())

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# ==========================================
# 1. 페이지 레이아웃 및 제목 짤림 방지 CSS 리파이닝
# ==========================================
st.set_page_config(layout="wide", page_title="청주 vs 송도")

st.markdown("""
    <style>
    /* 전체 여백 조정 */
    .block-container { max-width: 1400px; padding-top: 2rem; padding-bottom: 3rem; margin: 0 auto; }
    
    /* 상단 메인 타이틀 짤림 방지 및 안정적인 폰트 렌더링 */
    .main-title { 
        text-align: center; 
        font-size: 42px !important; 
        font-weight: 800; 
        color: #1E3A8A; 
        line-height: 1.5 !important;
        margin-bottom: 8px;
        padding: 5px 0;
    }
    .sub-info-text { text-align: center; font-size: 15px; color: #555555; margin-bottom: 25px; }
    h3, h4, h5 { text-align: center; font-weight: 700; color: #2C3E50; margin-top: 15px; }
    
    /* 투자 자본 통계 브리핑 카드 세팅 */
    .stMetric { border: 2px solid #E5E7EB; padding: 20px; border-radius: 12px; background-color: #F8FAFC; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #0F172A; font-weight: 800; text-align: center; }
    div[data-testid="stMetricLabel"] { font-size: 15px !important; color: #475569 !important; font-weight: 600; text-align: center; }
    
    /* 연도 버튼 레이아웃 최적화 */
    .stButton>button { 
        width: 100%; 
        padding: 6px 2px !important; 
        font-size: 13px !important; 
        font-weight: 700 !important; 
        border-radius: 6px !important;
        min-width: 45px;
    }
    
    /* 하단 탭 메뉴 가독성 증대 */
    .stTabs [data-baseweb="tab"] { font-size: 16px !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 자본 단위 변환 유틸리티 함수 (조/억 자동 표기)
# ==========================================
def format_currency(money_in_eok):
    if money_in_eok >= 10000:
        cho = money_in_eok // 10000
        eok = money_in_eok % 10000
        if eok > 0:
            return f"{cho}조 {eok:,}억 원"
        return f"{cho}조 원"
    else:
        return f"{money_in_eok:,}억 원"

# ==========================================
# 3. 1989년 ~ 2026년 마스터 시뮬레이션 데이터 구축
# ==========================================
years = list(range(1989, 2027))
data_list = []

for y in years:
    if y < 1999: cj_era = "LG반도체 시대"
    elif y < 2012: cj_era = "하이닉스 시대"
    else: cj_era = "SK하이닉스 시대"
    
    if y < 1994: sd_era = "개발 이전 바다"
    elif y <= 2002: sd_era = "갯벌 매립 단계"
    elif y <= 2009: sd_era = "인프라 구축기"
    else: sd_era = "국제도시 완성기"

    idx = y - 1989
    cj_pop = 420000 + (idx * 10500) if y < 2014 else 830000 + (y - 2014) * 3500
    cj_gdp = 5.2 + (idx * 0.8) if y < 2012 else 23.5 + (y - 2012) * 2.8
    cj_float = 180000 + (idx * 8500)
    
    if y < 1994:
        sd_pop, sd_gdp, sd_float, sd_foreign = 0, 0.0, 0, 0.0
    elif y <= 2002:
        sd_pop, sd_gdp, sd_float, sd_foreign = 0, 0.5 + (y-1994)*0.2, 5000 + (y-1994)*2500, 0.0
    else:
        sd_idx = y - 2002
        sd_pop = int(sd_idx * 9200)
        sd_gdp = 2.5 + (sd_idx * 1.7)
        sd_float = 35000 + (sd_idx * 14000)
        sd_foreign = min(1.2 + (sd_idx * 0.21), 6.8)

    if y < 1999: cj_gov, cj_pvt = idx * 150, idx * 800
    elif y < 2012: cj_gov, cj_pvt = 1500 + (y-1999)*220, 8000 + (y-1999)*2800
    else: cj_gov, cj_pvt = 4360 + (y-2012)*600, 44400 + (y-2012)*28000

    if y < 1994: sd_gov, sd_pvt = 0, 0
    elif y <= 2002: sd_gov, sd_pvt = (y-1994)*900, (y-1994)*600
    elif y <= 2009: sd_gov, sd_pvt = 7200 + (y-2002)*1800, 4800 + (y-2002)*3200
    else: sd_gov, sd_pvt = 19800 + (y-2009)*3100, 27200 + (y-2009)*7200

    data_list.append([y, cj_era, sd_era, cj_pop, cj_gdp, cj_float, sd_pop, sd_gdp, sd_float, sd_foreign, cj_gov, cj_pvt, sd_gov, sd_pvt])

df = pd.DataFrame(data_list, columns=[
    '연도', '청주기업단계', '송도개발단계', '청주인구', '청주GDP', '청주유동인구', 
    '송도인구', '송도GDP', '송도유동인구', '송도외국인비율', '청주국가투자', '청주민간투자', '송도국가투자', '송도민간투자'
])

# ==========================================
# 4. 5글자 메인 타이틀 및 1년 단위 정밀 버튼 바
# ==========================================
st.markdown('<div class="main-title">청주 vs 송도</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-info-text">원하는 연도 버튼을 클릭하면 전체 그리드 지표가 1년 단위로 동기화됩니다.</div>', unsafe_allow_html=True)

if "global_target_year" not in st.session_state:
    st.session_state.global_target_year = 2026

st.write("##### 📅 연도 직접 클릭 패널 (1년 단위 정밀 변환기)")

cols_p1 = st.columns(13)
cols_p2 = st.columns(13)
cols_p3 = st.columns(12)
all_cols = cols_p1 + cols_p2 + cols_p3

for index, year_val in enumerate(years):
    with all_cols[index]:
        btn_label = f"🎯{year_val}" if st.session_state.global_target_year == year_val else f"{year_val}"
        if st.button(btn_label, key=f"btn_yr_{year_val}"):
            st.session_state.global_target_year = year_val

selected_year = st.session_state.global_target_year
row = df[df['연도'] == selected_year].iloc[0]

st.info(f"📊 **현재 데이터 시뮬레이션 타임라인: {selected_year}년** | 🏭 청주: {row['청주기업단계']} | 🏙️ 송도: {row['송도개발단계']}")

# ==========================================
# 5. 공간 지리 정보 맵 레이아웃
# ==========================================
map_col1, map_col2 = st.columns(2)

with map_col1:
    st.markdown("### 🗺️ 청주 반도체 공장 중심권역")
    m_cj = folium.Map(location=[36.6505, 127.4335], zoom_start=13, tiles="OpenStreetMap", zoom_control=False)
    folium.CircleMarker(
        location=[36.6505, 127.4335], radius=min(row['청주인구'] / 15000, 50),
        color="#1E3A8A", fill=True, fill_color="#3B82F6", fill_opacity=0.45,
        tooltip=f"청주 상주인구: {row['청주인구']:,} 명"
    ).add_to(m_cj)
    if selected_year >= 2012:
        folium.PolyLine(locations=[[37.5665, 126.9780], [36.6505, 127.4335]], color="#EF4444", weight=4, opacity=0.7).add_to(m_cj)
    st_folium(m_cj, width=650, height=340, key="map_cheongju_v6")

with map_col2:
    st.markdown("### 🗺️ 인천 송도국제도시 개발권역")
    m_sd = folium.Map(location=[37.3925, 126.6385], zoom_start=13, tiles="OpenStreetMap", zoom_control=False)
    if selected_year >= 1994:
        folium.CircleMarker(
            location=[37.3925, 126.6385], radius=min(row['송도인구'] / 3000, 50) if row['송도인구'] > 0 else 3,
            color="#065F46", fill=True, fill_color="#10B981", fill_opacity=0.45,
            tooltip=f"송도 상주인구: {row['송도인구']:,} 명"
        ).add_to(m_sd)
        folium.PolyLine(locations=[[37.4485, 126.4512], [37.3925, 126.6385]], color="#F97316", weight=4, opacity=0.7).add_to(m_sd)
    st_folium(m_sd, width=650, height=340, key="map_songdo_v6")

# ==========================================
# 6. 실시간 자본 투자 요약 정보 브리핑 (조/억 자동 전환 적용)
# ==========================================
st.write("---")
st.markdown("### 💰 실시간 누적 예산 및 투자 자본 통계 브리핑")
inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)

inv_col1.metric("🏭 청주 누적 민간 자본", format_currency(row['청주민간투자']))
inv_col2.metric("🏛️ 청주 누적 국가 예산", format_currency(row['청주국가투자']))
inv_col3.metric("🏙️ 송도 누적 민간/개발 자본", format_currency(row['송도민간투자']))
inv_col4.metric("🏛️ 송도 누적 국가 예산", format_currency(row['송도국가투자']))
st.write("---")

# ==========================================
# 7. 세부 항목 시각화 분석 (GDP 게이지 짤림 버그 전면 해결)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📈 1. 경제 규모(GDP) 추이", "👥 2. 상주 및 유동인구 구조 분석", "📊 3. 인구 유입 세부 속성 인포그래픽"])

with tab1:
    st.markdown("#### 💡 연도별 지역 총생산(GDP) 실시간 성장 격차")
    gdp_col1, gdp_col2 = st.columns(2)
    
    # 💡 [핵심 해결 조치] 내부 여백 마진 상단 패딩(t=80)을 대폭 주어 글씨가 위 경계에 짤리지 않게 전면 조정
    with gdp_col1:
        fig_gdp_cj = go.Figure(go.Indicator(
            mode = "gauge+number+delta", value = row['청주GDP'],
            delta = {'reference': 5.2, 'prefix': "초기 대비 +", 'suffix': " 조 원"},
            title = {'text': "<b>청주 경제 총생산</b>", 'font': {'size': 22, 'color': '#1E3A8A'}},
            gauge = {'axis': {'range': [None, 65], 'ticksuffix': "조"}, 'bar': {'color': "#1E40AF"}}
        ))
        fig_gdp_cj.update_layout(height=280, margin=dict(t=80, b=20, l=40, r=40), paper_bgcolor="#F8F9FA")
        st.plotly_chart(fig_gdp_cj, use_container_width=True)
        
    with gdp_col2:
        fig_gdp_sd = go.Figure(go.Indicator(
            mode = "gauge+number+delta", value = row['송도GDP'],
            delta = {'reference': 0.5, 'prefix': "초기 대비 +", 'suffix': " 조 원"},
            title = {'text': "<b>송도 경제 총생산</b>", 'font': {'size': 22, 'color': '#065F46'}},
            gauge = {'axis': {'range': [None, 65], 'ticksuffix': "조"}, 'bar': {'color': "#065F46"}}
        ))
        fig_gdp_sd.update_layout(height=280, margin=dict(t=80, b=20, l=40, r=40), paper_bgcolor="#F8F9FA")
        st.plotly_chart(fig_gdp_sd, use_container_width=True)

with tab2:
    st.markdown("#### 💡 상주인구수 vs 일일 평균 유동인구 배치 분석 (수치 시인성 업그레이드)")
    pop_col1, pop_col2 = st.columns(2)
    
    with pop_col1:
        categories = ['상주 인구수', '일일 유동인구']
        values_cj = [row['청주인구'], row['청주유동인구']]
        
        fig_bar_cj = go.Figure(data=[go.Bar(
            x=categories, y=values_cj,
            text=[f"{v:,} 명" for v in values_cj], textposition='auto',
            marker_color=['#1E40AF', '#60A5FA'], textfont=dict(size=16, color='white')
        )])
        fig_bar_cj.update_layout(
            title=f"<b>{selected_year}년 청주 인구 볼륨 현황</b>",
            yaxis=dict(title="인구수 (명)", tickformat=","),
            height=340, margin=dict(t=50, b=30)
        )
        st.plotly_chart(fig_bar_cj, use_container_width=True)
        
    with pop_col2:
        values_sd = [row['송도인구'], row['송도유동인구']]
        
        fig_bar_sd = go.Figure(data=[go.Bar(
            x=categories, y=values_sd,
            text=[f"{v:,} 명" for v in values_sd], textposition='auto',
            marker_color=['#065F46', '#34D399'], textfont=dict(size=16, color='white')
        )])
        fig_bar_sd.update_layout(
            title=f"<b>{selected_year}년 송도 인구 볼륨 현황</b>",
            yaxis=dict(title="인구수 (명)", tickformat=","),
            height=340, margin=dict(t=50, b=30)
        )
        st.plotly_chart(fig_bar_sd, use_container_width=True)

with tab3:
    st.markdown("#### 💡 전입 유입 인구의 정밀 계층 구조 분석")
    prop_col1, prop_col2 = st.columns(2)
    
    with prop_col1:
        st.write("<h5 style='text-align:center;'>🏭 청주 반도체 단지 전입 인구 핵심 비율</h5>", unsafe_allow_html=True)
        if selected_year < 2012:
            labels, values = ['20대 청년 근로자', '30대 엔지니어', '기타 배후 인력'], [55, 25, 20]
        else:
            labels, values = ['20-30대 연구원', '40대 전문 엔지니어', '협력사/주거 가족'], [45, 30, 25]
            
        fig_pie_cj = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=.3,
            textinfo='label+percent',
            textfont=dict(size=14, color='#FFFFFF'),
            marker=dict(colors=['#1E3A8A', '#2563EB', '#93C5FD'])
        )])
        fig_pie_cj.update_layout(height=320, showlegend=True, legend=dict(orientation="h", y=-0.12), margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_pie_cj, use_container_width=True)

    with prop_col2:
        st.write("<h5 style='text-align:center;'>🏙️ 인천 송도 국제지구 전입 인구 핵심 비율</h5>", unsafe_allow_html=True)
        if selected_year < 2005:
            labels, values = ['초기 이주 가구', '인프라 건설 근로자'], [30, 70]
        else:
            labels, values = ['3040 바이오 연구직', '국제학교 교육 이주층', '외국인 유학생 및 교원'], [40, 45, 15]
            
        fig_pie_sd = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=.3,
            textinfo='label+percent',
            textfont=dict(size=14, color='#FFFFFF'),
            marker=dict(colors=['#047857', '#10B981', '#A7F3D0'])
        )])
        fig_pie_sd.update_layout(height=320, showlegend=True, legend=dict(orientation="h", y=-0.12), margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_pie_sd, use_container_width=True)