import re
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st


# ==========================================
# 기본 설정
# ==========================================
st.set_page_config(
    page_title="Meal Pattern Finder",
    page_icon="🍱",
    layout="wide"
)

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/songtan_meals_184.csv"
)


# ==========================================
# 데이터 불러오기 및 전처리
# ==========================================
@st.cache_data
def load_data():

    df = pd.read_csv(
        DATA_URL,
        encoding="utf-8"
    )

    required_columns = ["날짜", "식사", "메뉴"]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필요한 열이 없습니다: {missing_columns}"
        )

    df = df[required_columns].dropna(
        subset=["메뉴"]
    )

    def clean_menu(menu):

        menu = str(menu)

        # 괄호와 괄호 안의 내용 제거
        menu = re.sub(
            r"\([^()]*\)",
            "",
            menu
        )

        # 대괄호 안의 내용도 제거
        menu = re.sub(
            r"\[[^\]]*\]",
            "",
            menu
        )

        return menu.strip()

    transactions = []

    for menu_text in df["메뉴"]:

        menus = str(menu_text).split("|")

        cleaned_menus = set()

        for menu in menus:

            cleaned = clean_menu(menu)

            if cleaned:
                cleaned_menus.add(cleaned)

        transactions.append(
            sorted(cleaned_menus)
        )

    return df, transactions


# ==========================================
# 연관 규칙 계산
# ==========================================
def make_rules(transactions):

    total_days = len(transactions)

    menu_count = {}
    pair_count = {}

    # 메뉴별 출현 횟수와 메뉴 쌍 계산
    for menus in transactions:

        for menu in menus:

            menu_count[menu] = (
                menu_count.get(menu, 0) + 1
            )

        for a, b in combinations(menus, 2):

            pair = (a, b)

            pair_count[pair] = (
                pair_count.get(pair, 0) + 1
            )

    rules = []

    # 메뉴 쌍마다 양방향 규칙 생성
    for (a, b), together in pair_count.items():

        # 지지도
        support = together / total_days

        # A -> B
        confidence_ab = (
            together / menu_count[a]
        )

        lift_ab = (
            confidence_ab
            / (menu_count[b] / total_days)
        )

        rules.append({
            "조건": a,
            "결과": b,
            "동시": together,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        confidence_ba = (
            together / menu_count[b]
        )

        lift_ba = (
            confidence_ba
            / (menu_count[a] / total_days)
        )

        rules.append({
            "조건": b,
            "결과": a,
            "동시": together,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return rules_df, len(pair_count), menu_count


# ==========================================
# 앱 제목
# ==========================================
st.title("🍱 Meal Pattern Finder")

st.write(
    "송탄고 중식 184일의 급식 데이터를 분석하여 "
    "함께 나오는 메뉴의 규칙을 찾아봅니다."
)

st.caption(
    "A data analysis app for discovering "
    "school meal patterns."
)


# ==========================================
# 데이터 불러오기
# ==========================================
try:

    original_df, transactions = load_data()

    rules_df, pair_count, menu_count = make_rules(
        transactions
    )

except Exception as e:

    st.error(
        f"데이터를 불러오는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


# ==========================================
# 기본 통계
# ==========================================
total_days = len(transactions)

all_menus = set()

for menus in transactions:

    all_menus.update(menus)

menu_types = len(all_menus)

st.markdown(
    f"**급식 일수:** {total_days}일　 |　 "
    f"**메뉴 종류 수:** {menu_types}개　 |　 "
    f"**함께 나온 메뉴 쌍 수:** {pair_count}쌍"
)

st.divider()


# ==========================================
# 메뉴 선택
# ==========================================
st.subheader("🔍 메뉴별 규칙 찾기")

menu_options = [
    "전체 메뉴"
] + sorted(all_menus)

selected_menu = st.selectbox(
    "메뉴 선택",
    menu_options,
    help="선택한 메뉴가 포함된 규칙만 표시합니다."
)


# ==========================================
# 규칙 필터링
# ==========================================
filtered_rules = rules_df.copy()

if selected_menu != "전체 메뉴":

    filtered_rules = filtered_rules[
        (
            filtered_rules["조건"]
            == selected_menu
        )
        |
        (
            filtered_rules["결과"]
            == selected_menu
        )
    ]


# ==========================================
# 정렬
# ==========================================
sort_option = st.selectbox(
    "정렬 기준",
    [
        "향상도 순",
        "신뢰도 순",
        "동시 순"
    ]
)

sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_rules = filtered_rules.sort_values(
    by=[
        sort_column,
        "신뢰도",
        "동시"
    ],
    ascending=[
        False,
        False,
        False
    ]
).reset_index(drop=True)


# ==========================================
# 규칙 표
# ==========================================
st.subheader("📋 함께 나온 메뉴 규칙")

if filtered_rules.empty:

    st.info(
        "표시할 규칙이 없습니다."
    )

else:

    display_df = filtered_rules.copy()

    # 백분율로 변환
    display_df["지지도"] = (
        display_df["지지도"] * 100
    ).map(
        lambda x: f"{x:.2f}%"
    )

    display_df["신뢰도"] = (
        display_df["신뢰도"] * 100
    ).map(
        lambda x: f"{x:.2f}%"
    )

    display_df["향상도"] = (
        display_df["향상도"]
    ).map(
        lambda x: f"{x:.3f}"
    )

    st.dataframe(
        display_df[
            [
                "조건",
                "결과",
                "동시",
                "지지도",
                "신뢰도",
                "향상도"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"현재 표시 중인 규칙: "
        f"{len(filtered_rules)}개"
    )


# ==========================================
# 향상도 상위 10개 그래프
# ==========================================
st.divider()

st.subheader("📊 향상도 TOP 10")

if filtered_rules.empty:

    st.info(
        "그래프를 그릴 규칙이 없습니다."
    )

else:

    top10 = (
        filtered_rules
        .sort_values(
            by=[
                "향상도",
                "신뢰도",
                "동시"
            ],
            ascending=[
                False,
                False,
                False
            ]
        )
        .head(10)
        .copy()
    )

    # 그래프에 표시할 규칙 이름
    top10["규칙"] = (
        top10["조건"]
        + " → "
        + top10["결과"]
    )

    # 가로 막대그래프
    fig = px.bar(
        top10.sort_values(
            "향상도",
            ascending=True
        ),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.2%",
            "신뢰도": ":.2%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도",
            "규칙": "메뉴 규칙"
        },
        title="향상도가 높은 메뉴 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=max(
            400,
            len(top10) * 45
        ),
        xaxis_title="향상도",
        yaxis_title="",
        margin=dict(
            l=20,
            r=80,
            t=60,
            b=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# 지표 설명
# ==========================================
st.divider()

with st.expander("📖 지표 설명 보기"):

    st.markdown("""
    - **조건:** 규칙의 시작 메뉴
    - **결과:** 조건 메뉴와 함께 나온 메뉴
    - **동시:** 두 메뉴가 함께 나온 급식 일수
    - **지지도:** 두 메뉴가 함께 나온 비율
    - **신뢰도:** 조건 메뉴가 나왔을 때 결과 메뉴도 나온 비율
    - **향상도:** 두 메뉴의 동시 출현이 독립적인 경우보다 얼마나 자주 나타나는지 나타내는 값

    향상도가 1보다 크면 두 메뉴가 독립적인 경우보다 함께 나오는 경향이 강합니다.

    향상도가 1이면 독립적인 관계이며, 1보다 작으면 함께 나오는 경향이 약합니다.

    조건과 결과를 바꾸면 신뢰도는 달라질 수 있지만, 지지도와 향상도는 같습니다.

