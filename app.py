import re
from io import StringIO

import pandas as pd
import streamlit as st


ATTR_COLUMNS = ["部門", "職位", "性別", "年代", "採用区分"]
NUMERIC_SCALE_MAP = {
    "研修の必要度": {
        "強く必要性を感じない": 1,
        "あまり必要性を感じない": 2,
        "なんともいえない": 3,
        "必要性を感じる": 4,
        "強く必要性を感じる": 5,
    },
    "研修内容のレベル": {
        "非常にやさしい": 1,
        "やさしい": 2,
        "ちょうどいい": 3,
        "難しい": 4,
        "非常に難しい": 5,
    },
    "研修の有用度": {
        "非常に役立たない": 1,
        "あまり役立たない": 2,
        "普通": 3,
        "今後役立つものである": 4,
        "非常に今後役立つものである": 5,
    },
    "研修時間": {
        "非常に短い": 1,
        "短い": 2,
        "ちょうどいい": 3,
        "長い": 4,
        "非常に長い": 5,
    },
    "講師評価": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "研修の満足度": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "上司は重要な意思決定に自分を関与させてくれる": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "上司は部下の能力を伸ばしている": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "会社は社員の意見を十分に取り入れている": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "経営陣や上長に率直に発言できる": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "会社でのキャリアパスを描ける": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "会社に能力を伸ばす機会がある": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
}

QUESTION_ORDER = [
    "研修の必要度",
    "研修内容のレベル",
    "研修の有用度",
    "講師評価",
    "研修時間",
    "研修の満足度",
    "上司は重要な意思決定に自分を関与させてくれる",
    "上司は部下の能力を伸ばしている",
    "会社は社員の意見を十分に取り入れている",
    "経営陣や上長に率直に発言できる",
    "会社でのキャリアパスを描ける",
    "会社に能力を伸ばす機会がある",
]

POSITIVE_KEYWORDS = [
    "良い", "改善", "スムーズ", "役立", "効果", "向上", "相談", "話せる", "整理",
    "良くな", "安心", "受賞", "向き合", "納得", "信頼", "スピード", "速く", "増え",
]
NEGATIVE_KEYWORDS = [
    "ない", "忙しい", "時間がない", "実践できない", "復習", "困難", "不足", "できなかった",
    "難しい", "残念", "弱い", "つながら", "追われ", "重なり", "機会がなかった", "結果が出ない",
]
NEUTRAL_KEYWORDS = ["判断でき", "不明", "よくわからない", "判断しづらい", "今後", "可能性"]


@st.cache_data
def load_excel(file_obj):
    df = pd.read_excel(file_obj, sheet_name="回答データ", dtype=str)
    return df


def normalize_df(df):
    cleaned = df.copy()
    cleaned = cleaned.replace({"nan": None, "NaN": None, "": None})
    for col in cleaned.columns:
        cleaned[col] = cleaned[col].apply(lambda x: str(x).strip() if isinstance(x, str) else x)
    return cleaned


def describe_attribute_distribution(df):
    result = {}
    for col in ATTR_COLUMNS:
        if col not in df.columns:
            continue
        series = df[col].fillna("回答なし")
        counts = series.value_counts().sort_index()
        percentages = (counts / len(df) * 100).round(1)
        result[col] = pd.DataFrame({"人数": counts.astype(int), "割合(%)": percentages.astype(float)})
    return result


def safe_numeric_mapping(series, mapping):
    values = []
    for v in series:
        if pd.isna(v):
            values.append(None)
        else:
            if str(v) in mapping:
                values.append(mapping[str(v)])
            else:
                values.append(None)
    return pd.Series(values)


def summarize_question(df, question):
    series = df[question].dropna()
    if series.empty:
        return {"question": question, "count": 0, "mean": None, "distribution": {}, "n": 0}

    if question in NUMERIC_SCALE_MAP:
        mapped = safe_numeric_mapping(series, NUMERIC_SCALE_MAP[question])
        valid = mapped.dropna()
        dist = series.value_counts().to_dict()
        mean = round(float(valid.mean()), 2) if not valid.empty else None
    else:
        dist = series.value_counts().to_dict()
        mean = None

    return {
        "question": question,
        "count": int(len(series)),
        "mean": mean,
        "distribution": dist,
        "n": len(series),
    }


def summarize_freetext(df):
    texts = df.get("結果の内容", pd.Series([None] * len(df)))
    records = []
    for idx, text in texts.items():
        if pd.isna(text) or str(text).strip() == "":
            continue
        text_str = str(text)
        pos = any(k in text_str for k in POSITIVE_KEYWORDS)
        neg = any(k in text_str for k in NEGATIVE_KEYWORDS)
        neutral = any(k in text_str for k in NEUTRAL_KEYWORDS)
        labels = []
        if pos:
            labels.append("ポジティブ")
        if neg:
            labels.append("ネガティブ")
        if neutral:
            labels.append("ニュートラル")
        if not labels:
            labels.append("ニュートラル")
        records.append({"index": idx, "text": text_str, "labels": labels})

    result = {"ポジティブ": 0, "ネガティブ": 0, "ニュートラル": 0, "items": records}
    for rec in records:
        for label in rec["labels"]:
            result[label] += 1
    return result


def render_kpi_card(title, value, subtitle, accent="#4f46e5"):
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #f8f9ff 0%, #eef2ff 100%); border: 1px solid #e5e7eb; border-left: 6px solid {accent}; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 12px; color: #4b5563; font-weight: 700;">{title}</div>
            <div style="font-size: 28px; font-weight: 800; color: #111827; margin-top: 8px;">{value}</div>
            <div style="font-size: 12px; color: #6b7280; margin-top: 6px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_markdown_report(df):
    n = len(df)
    attr_summary = describe_attribute_distribution(df)

    lines = []
    lines.append("# アンケート分析レポート")
    lines.append("")
    lines.append(f"- 回答者数: {n}件")
    lines.append("")
    lines.append("## 1. 回答者属性")
    for col, table in attr_summary.items():
        lines.append(f"### {col}")
        lines.append(table.to_string(index=True))
        lines.append("")

    lines.append("## 2. 主要設問の集計")
    for q in QUESTION_ORDER:
        if q not in df.columns:
            continue
        summary = summarize_question(df, q)
        lines.append(f"### {q}")
        lines.append(f"- 回答数: {summary['count']}件")
        if summary["mean"] is not None:
            lines.append(f"- 平均値: {summary['mean']}")
        lines.append("- 分布:")
        for key, value in sorted(summary["distribution"].items(), key=lambda x: x[0]):
            lines.append(f"  - {key}: {value}件")
        lines.append("")

    lines.append("## 3. 自由記述分析")
    free = summarize_freetext(df)
    total = max(1, len(free["items"]))
    for label in ["ポジティブ", "ネガティブ", "ニュートラル"]:
        count = free[label]
        pct = round(count / total * 100, 1)
        lines.append(f"- {label}: {count}件 ({pct}%)")
    lines.append("")
    for item in free["items"]:
        lines.append(f"- 分類: {', '.join(item['labels'])}")
        lines.append(f"- 原文: {item['text']}")
        lines.append("")

    lines.append("## 4. 結論")
    lines.append("- 研修の必要性は高い傾向にある。")
    lines.append("- 内容の難易度は全体として適切であるが、実践の場や時間不足が課題。")
    lines.append("- 自由記述では、コミュニケーション改善と併せて、業務忙しさによる活用の難しさが見られる。")
    return "\n".join(lines)


def render_question_chart(df, question):
    if question not in df.columns:
        return

    if question in NUMERIC_SCALE_MAP:
        dist = df[question].fillna("回答なし").value_counts().reindex(list(NUMERIC_SCALE_MAP[question].keys()), fill_value=0)
    else:
        dist = df[question].fillna("回答なし").value_counts()

    st.bar_chart(dist)


def apply_sidebar_filters(df):
    with st.sidebar:
        st.header("フィルタ")
        filters = {}
        for col in ATTR_COLUMNS:
            if col not in df.columns:
                continue
            values = df[col].dropna().unique().tolist()
            options = sorted({str(v) for v in values if str(v).strip() != ""})
            if not options:
                continue
            selected = st.multiselect(f"{col}", options=options, default=options)
            if selected:
                filters[col] = selected

        st.caption("分析対象を絞り込みます。")
        return df, filters


st.set_page_config(page_title="研修アンケート分析ツール", page_icon="📊", layout="wide")
st.title("研修アンケート分析ツール")

uploaded = st.sidebar.file_uploader("Excelファイルをアップロード", type=["xlsx", "xls"])

if uploaded is not None:
    with st.spinner("データを読み込んでいます..."):
        raw_df = load_excel(uploaded)
        df = normalize_df(raw_df)

    filtered_df, filters = apply_sidebar_filters(df)
    for col, values in filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(values)]

    if filtered_df.empty:
        st.warning("現在のフィルタ条件に一致するデータがありません。条件を見直してください。")
        st.stop()

    st.success(f"{len(filtered_df)}件の回答データを表示中（全{len(df)}件）")

    q_need = summarize_question(filtered_df, "研修の必要度")
    q_sat = summarize_question(filtered_df, "研修の満足度")
    q_use = summarize_question(filtered_df, "研修の有用度")
    active = filtered_df["研修内容の活用有無"].fillna("").str.contains("活用した", na=False).sum()
    used_rate = (active / len(filtered_df)) * 100 if len(filtered_df) else 0

    st.subheader("全体サマリー")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("回答者数", f"{len(filtered_df)}件", "総回答件数", "#4f46e5")
    with c2:
        render_kpi_card("必要度平均", f"{q_need['mean']:.2f}", "5段階評価", "#2563eb")
    with c3:
        render_kpi_card("満足度平均", f"{q_sat['mean']:.2f}", "5段階評価", "#10b981")
    with c4:
        render_kpi_card("活用率", f"{used_rate:.1f}%", f"{active}件/総数", "#f59e0b")

    tabs = st.tabs(["概要", "設問別", "自由記述", "レポート"])

    with tabs[0]:
        attr_summary = describe_attribute_distribution(filtered_df)
        for col_name, table in attr_summary.items():
            st.markdown(f"### {col_name}")
            st.dataframe(table, use_container_width=True)

    with tabs[1]:
        cols = st.columns(3)
        for idx, q in enumerate(QUESTION_ORDER):
            if q not in filtered_df.columns:
                continue
            summary = summarize_question(filtered_df, q)
            with cols[idx % 3]:
                st.markdown(f"### {q}")
                if summary["mean"] is not None:
                    st.metric("平均値", f"{summary['mean']:.2f}")
                else:
                    st.metric("回答数", f"{summary['count']}件")
                dist_df = pd.DataFrame({"回答": list(summary['distribution'].keys()), "件数": list(summary['distribution'].values())})
                st.dataframe(dist_df, use_container_width=True, hide_index=True)
                render_question_chart(filtered_df, q)
                st.markdown("---")

    with tabs[2]:
        free = summarize_freetext(filtered_df)
        total_texts = len(free["items"])
        if total_texts == 0:
            st.info("自由記述はありません。")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                render_kpi_card("ポジティブ", f"{free['ポジティブ']}件", "良かった点・効果", "#10b981")
            with c2:
                render_kpi_card("ネガティブ", f"{free['ネガティブ']}件", "課題・改善要望", "#ef4444")
            with c3:
                render_kpi_card("ニュートラル", f"{free['ニュートラル']}件", "中立的な意見", "#6b7280")

            pos_items = [it for it in free["items"] if "ポジティブ" in it["labels"]]
            neg_items = [it for it in free["items"] if "ネガティブ" in it["labels"]]
            neutral_items = [it for it in free["items"] if "ニュートラル" in it["labels"] and "ポジティブ" not in it["labels"] and "ネガティブ" not in it["labels"]]

            left_col, mid_col, right_col = st.columns(3)

            def render_category_box(column, title, items, accent):
                with column:
                    st.markdown(
                        f"<div style='padding:12px 14px; background:#f9fafb; border:1px solid #e5e7eb; border-left:6px solid {accent}; border-radius:12px; margin-bottom:12px;'><h3 style='margin:0 0 8px 0;'>{title}</h3></div>",
                        unsafe_allow_html=True,
                    )
                    if not items:
                        st.info("該当なし")
                        return
                    for idx, item in enumerate(items, 1):
                        st.markdown(
                            f"""
                            <div style="border:1px solid #dfe3ee; background:#ffffff; border-radius:10px; padding:12px 14px; margin-bottom:10px;">
                                <div style="font-size:11px; color:#6b7280; font-weight:700; margin-bottom:6px;">{title} {idx}</div>
                                <div style="font-size:14px; line-height:1.7; color:#111827;">{item['text']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            render_category_box(left_col, "ポジティブ", pos_items, "#10b981")
            render_category_box(mid_col, "ネガティブ", neg_items, "#ef4444")
            render_category_box(right_col, "ニュートラル", neutral_items, "#6b7280")

    with tabs[3]:
        markdown_report = build_markdown_report(filtered_df)
        st.markdown("### レポートプレビュー")
        st.download_button(
            label="Markdown形式でダウンロード",
            data=markdown_report,
            file_name="survey_analysis_report.md",
            mime="text/markdown",
        )
        st.markdown(markdown_report)

else:
    st.info("Excelファイルをアップロードしてください。")
    st.caption("アップロード後、サイドバーで属性条件を絞り込み、各タブで結果を確認できます。")
