import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

st.set_page_config(page_title="研修アンケート分析ツール", layout="wide")
plt.rcParams["font.sans-serif"] = ["Hiragino Sans", "YuGothic", "MS Gothic"]
plt.rcParams["axes.unicode_minus"] = False

st.title("📊 研修アンケート分析ツール")

uploaded = st.file_uploader("Excelファイルをアップロード", type=["xlsx", "xls", "csv"])

if uploaded:
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded, sep="\t")
        else:
            xls = pd.ExcelFile(uploaded)
            sheet = xls.sheet_names[0]
            df = pd.read_excel(uploaded, sheet_name=sheet)

        # ===== データの準備 =====
        ATTRS = ["部門", "職位", "性別", "年代", "採用区分"]
        SCALE5_ITEMS = ["講師評価", "研修の満足度", "活用結果の程度", "上司は重要な意思決定に自分を関与させてくれる", "上司は部下の能力を伸ばしている", "会社は社員の意見を十分に取り入れている", "経営陣や上長に率直に発言できる", "会社でのキャリアパスを描ける", "会社に能力を伸ばす機会がある"]
        TEXT_ITEMS = ["結果の内容"]

        # ===== タブUI =====
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["全体サマリー", "設問別分析", "自由記述", "属性別分析", "レポート", "部門別"])

        # ===== TAB1: 全体サマリー =====
        with tab1:
            st.header("全体サマリー")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("回答者数", f"{len(df)}件")
            with col2:
                st.metric("総回答件数", f"{len(df) * len(SCALE5_ITEMS)}件")
            
            # 必要度平均
            if "講師評価" in df.columns:
                avg_eval = pd.to_numeric(df["講師評価"], errors="coerce").mean()
                with col3:
                    st.metric("講師評価平均", f"{avg_eval:.2f}", "5段階評価")
            
            # 満足度平均
            if "研修の満足度" in df.columns:
                avg_sat = pd.to_numeric(df["研修の満足度"], errors="coerce").mean()
                with col4:
                    st.metric("満足度平均", f"{avg_sat:.2f}", "5段階評価")

            # 活用率
            if "研修内容の活用有無" in df.columns:
                active = (df["研修内容の活用有無"] == "研修で学んだことを、活用した").sum()
                rate = active / len(df) * 100
                st.metric("活用率", f"{rate:.1f}%", f"{active}件/総数{len(df)}件")

        # ===== TAB2: 設問別分析 =====
        with tab2:
            st.header("設問別分析")
            for col in SCALE5_ITEMS:
                if col not in df.columns:
                    continue
                st.subheader(col)
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if s.empty:
                    continue

                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("平均", f"{s.mean():.2f}")
                with col2: st.metric("回答数", len(s))
                with col3: st.metric("中央値", f"{s.median():.2f}")
                with col4: st.metric("最大値", f"{s.max():.0f}")

                vc = s.value_counts().sort_index()
                fig, ax = plt.subplots(figsize=(8, 4))
                vc.plot(kind="bar", ax=ax, color="#4C78A8")
                ax.set_title(col)
                ax.set_ylabel("人数")
                st.pyplot(fig)

        # ===== TAB3: 自由記述 =====
        with tab3:
            st.header("自由記述分析")
            for col in TEXT_ITEMS:
                if col not in df.columns:
                    continue
                st.subheader(col)
                texts = df[col].dropna().astype(str).tolist()
                if not texts:
                    st.info("データなし")
                    continue

                pos_kw = ["よかった", "良かった", "役立った", "満足", "効果", "勉強", "理解", "楽しかった"]
                neg_kw = ["不満", "改善", "難しい", "不十分", "困った", "問題", "残念", "わかりにくい"]

                pos = sum(1 for t in texts if any(k in t for k in pos_kw))
                neg = sum(1 for t in texts if any(k in t for k in neg_kw))
                neu = len(texts) - pos - neg

                col1, col2, col3 = st.columns(3)
                with col1: st.metric("ポジティブ", f"{pos}件 ({pos/len(texts)*100:.1f}%)")
                with col2: st.metric("ネガティブ", f"{neg}件 ({neg/len(texts)*100:.1f}%)")
                with col3: st.metric("ニュートラル", f"{neu}件 ({neu/len(texts)*100:.1f}%)")

                st.write("**サンプルコメント:**")
                for t in texts[:5]:
                    if str(t).strip() and t != "自由記述":
                        st.code(t)

        # ===== TAB4: 属性別分析 =====
        with tab4:
            st.header("属性別クロス集計")
            attr = st.selectbox("属性を選択", ATTRS)
            if attr in df.columns:
                for q in SCALE5_ITEMS[:5]:
                    if q not in df.columns:
                        continue
                    temp = pd.DataFrame({
                        "attr": df[attr].fillna("未回答").astype(str),
                        "score": pd.to_numeric(df[q], errors="coerce")
                    }).dropna()
                    if temp.empty:
                        continue

                    grouped = temp.groupby("attr")["score"].mean().sort_values(ascending=False)
                    fig, ax = plt.subplots(figsize=(9, 5))
                    grouped.plot(kind="bar", ax=ax, color="#F58518")
                    ax.set_title(f"{q} / {attr}")
                    ax.set_ylabel("平均値")
                    plt.xticks(rotation=35, ha="right")
                    st.pyplot(fig)

        # ===== TAB5: レポート =====
        with tab5:
            st.header("レポート")
            means = []
            for col in SCALE5_ITEMS:
                if col in df.columns:
                    s = pd.to_numeric(df[col], errors="coerce").dropna()
                    if not s.empty:
                        means.append((col, s.mean()))

            means.sort(key=lambda x: x[1])
            
            st.write("**低評価項目（改善が必要）:**")
            for col, avg in means[:3]:
                st.write(f"- {col}: 平均 {avg:.2f}")

            st.write("\n**改善提案:**")
            st.write("1️⃣ 低評価項目の具体的な改善策を検討する")
            st.write("2️⃣ 自由記述の課題コメントをテーマ別に分類する")
            st.write("3️⃣ 高評価項目は継続・強化する")

            if means:
                overall = np.mean([m[1] for m in means])
                if overall >= 4.0:
                    eval_text = "🟢 良好"
                elif overall >= 3.0:
                    eval_text = "🟡 概ね良好"
                else:
                    eval_text = "🔴 改善要"
                st.write(f"\n**総合評価: {eval_text}**")
                st.write(f"全体平均: {overall:.2f}")

        # ===== TAB6: 部門別 =====
        with tab6:
            st.header("部門別分析")
            if "部門" in df.columns:
                depts = df["部門"].unique()
                for dept in depts:
                    st.subheader(f"部門: {dept}")
                    dept_df = df[df["部門"] == dept]
                    st.write(f"回答数: {len(dept_df)}件")
                    
                    for col in SCALE5_ITEMS[:3]:
                        if col in df.columns:
                            s = pd.to_numeric(dept_df[col], errors="coerce").dropna()
                            if not s.empty:
                                st.write(f"- {col}: 平均 {s.mean():.2f}")

        st.success("✅ 分析完了")

    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())
