
import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

# =====================================
# 1. 網頁基本設定
# =====================================

st.set_page_config(
    page_title="微客電子報策略 AI Agent",
    page_icon="📊",
    layout="wide"
)

st.title("📊 微客電子報策略 AI Agent")
st.caption("Donor Intelligence & Email Strategy")

st.sidebar.title("功能選單")

page = st.sidebar.radio(
    "請選擇功能",
    ["資料上傳", "捐款數據 Dashboard", "AI 策略分析"]
)


# =====================================
# 2. 共用函數
# =====================================

def read_file(file):
    """讀取 CSV 或 Excel，保留捐款人代碼格式。"""
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(
            file,
            dtype={"捐款人代碼": str},
            encoding="utf-8-sig"
        )

    return pd.read_excel(
        file,
        dtype={"捐款人代碼": str}
    )


def validate_columns(df, required, name):
    """檢查必要欄位。"""
    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        return f"{name} 缺少欄位：{', '.join(missing)}"

    return None


def get_api_key():
    """安全讀取 API Key，不顯示金鑰。"""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if isinstance(key, str):
            return key.strip()
    except Exception:
        pass

    return ""


def get_model():
    """讀取 API 模型設定。"""
    try:
        return st.secrets.get(
            "OPENAI_MODEL",
            "gpt-4.1-mini"
        )
    except Exception:
        return "gpt-4.1-mini"


# =====================================
# 3. 資料上傳頁面
# =====================================

if page == "資料上傳":

    st.header("📁 上傳微客捐款資料")

    st.write(
        "請依序上傳三份資料，"
        "系統將自動進行基本檢查。"
    )

    donor_file = st.file_uploader(
        "① 捐款人名單",
        type=["csv", "xlsx"],
        key="donor_file"
    )

    donation_file = st.file_uploader(
        "② 一年內捐款紀錄",
        type=["csv", "xlsx"],
        key="donation_file"
    )

    contact_file = st.file_uploader(
        "③ 接觸時間軸",
        type=["csv", "xlsx"],
        key="contact_file"
    )

    if donor_file and donation_file and contact_file:

        try:
            donors = read_file(donor_file)
            donations = read_file(donation_file)
            contacts = read_file(contact_file)

            # 清除欄位名稱前後空白
            for df in [donors, donations, contacts]:
                df.columns = df.columns.str.strip()

            # 必要欄位
            required_donor = ["捐款人代碼"]

            required_donation = [
                "捐款人代碼",
                "收到日期",
                "金額"
            ]

            required_contact = [
                "捐款人代碼",
                "接觸日期",
                "接觸類型"
            ]

            errors = []

            for name, df, required in [
                ("捐款人名單", donors, required_donor),
                ("捐款紀錄", donations, required_donation),
                ("接觸時間軸", contacts, required_contact)
            ]:
                error = validate_columns(
                    df, required, name
                )
                if error:
                    errors.append(error)

            if errors:
                for error in errors:
                    st.error(error)

            else:
                # 統一捐款人代碼
                for df in [donors, donations, contacts]:
                    df["捐款人代碼"] = (
                        df["捐款人代碼"]
                        .astype("string")
                        .str.strip()
                    )

                # 日期格式
                donations["收到日期"] = pd.to_datetime(
                    donations["收到日期"],
                    errors="coerce"
                )

                contacts["接觸日期"] = pd.to_datetime(
                    contacts["接觸日期"],
                    errors="coerce"
                )

                # 金額格式
                donations["金額"] = pd.to_numeric(
                    donations["金額"],
                    errors="coerce"
                )

                # 資料清理
                original_donations = len(donations)
                original_contacts = len(contacts)

                donations = donations.dropna(
                    subset=[
                        "捐款人代碼",
                        "收到日期",
                        "金額"
                    ]
                ).copy()

                contacts = contacts.dropna(
                    subset=[
                        "捐款人代碼",
                        "接觸日期",
                        "接觸類型"
                    ]
                ).copy()

                removed_donations = (
                    original_donations - len(donations)
                )

                removed_contacts = (
                    original_contacts - len(contacts)
                )

                # 檢查重複的捐款人代碼
                duplicate_donors = (
                    donors["捐款人代碼"]
                    .duplicated()
                    .sum()
                )

                # 儲存資料
                st.session_state["donors"] = donors
                st.session_state["donations"] = donations
                st.session_state["contacts"] = contacts

                # 新資料上傳後，清除舊 AI 報告
                st.session_state.pop("ai_report", None)

                st.success("✅ 三份資料上傳成功！")

                # 資料筆數
                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "捐款人名單",
                    f"{len(donors):,} 位"
                )

                c2.metric(
                    "捐款紀錄",
                    f"{len(donations):,} 筆"
                )

                c3.metric(
                    "接觸紀錄",
                    f"{len(contacts):,} 筆"
                )

                # 資料品質提醒
                if removed_donations > 0:
                    st.warning(
                        f"捐款紀錄有 {removed_donations} 筆"
                        "因必要欄位缺失而被排除。"
                    )

                if removed_contacts > 0:
                    st.warning(
                        f"接觸紀錄有 {removed_contacts} 筆"
                        "因必要欄位缺失而被排除。"
                    )

                if duplicate_donors > 0:
                    st.warning(
                        f"捐款人名單有 {duplicate_donors} 筆"
                        "重複的捐款人代碼，請確認資料。"
                    )

                st.divider()

                st.subheader("① 捐款人名單預覽")
                st.dataframe(
                    donors.head(10),
                    width="stretch"
                )

                st.subheader("② 捐款紀錄預覽")
                st.dataframe(
                    donations.head(10),
                    width="stretch"
                )

                st.subheader("③ 接觸時間軸預覽")
                st.dataframe(
                    contacts.head(10),
                    width="stretch"
                )

        except Exception as e:
            st.error(f"資料處理失敗：{e}")


# =====================================
# 4. Dashboard 頁面
# =====================================

elif page == "捐款數據 Dashboard":

    st.header("📈 微客捐款數據 Dashboard")

    required_keys = [
        "donors",
        "donations",
        "contacts"
    ]

    if not all(
        key in st.session_state
        for key in required_keys
    ):
        st.warning("請先上傳三份資料。")

    else:
        donors = st.session_state["donors"]
        donations = st.session_state["donations"]
        contacts = st.session_state["contacts"]

        # -----------------------------
        # 核心指標
        # -----------------------------

        total_amount = donations["金額"].sum()

        total_donors = (
            donations["捐款人代碼"].nunique()
        )

        donation_count = len(donations)

        avg_amount = (
            donations["金額"].mean()
            if donation_count > 0 else 0
        )

        st.subheader("📊 捐款概況")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "累計捐款金額",
            f"NT$ {total_amount:,.0f}"
        )

        c2.metric(
            "實際捐款人數",
            f"{total_donors:,}"
        )

        c3.metric(
            "捐款紀錄筆數",
            f"{donation_count:,}"
        )

        c4.metric(
            "平均單筆捐款",
            f"NT$ {avg_amount:,.0f}"
        )

        st.divider()

        # -----------------------------
        # 每月捐款趨勢
        # -----------------------------

        st.subheader("📈 每月捐款趨勢")

        if not donations.empty:

            monthly = (
                donations
                .assign(
                    月份=donations["收到日期"]
                    .dt.to_period("M")
                    .astype(str)
                )
                .groupby(
                    "月份",
                    as_index=False
                )["金額"]
                .sum()
            )

            fig_monthly = px.line(
                monthly,
                x="月份",
                y="金額",
                markers=True,
                title="每月捐款金額"
            )

            st.plotly_chart(
                fig_monthly,
                width="stretch"
            )

        else:
            st.info("目前沒有可分析的捐款紀錄。")

        # -----------------------------
        # 專案捐款分析
        # -----------------------------

        if "專案名稱" in donations.columns:

            st.subheader("🎯 各專案捐款金額")

            project_summary = (
                donations
                .groupby(
                    "專案名稱",
                    as_index=False
                )["金額"]
                .sum()
                .sort_values(
                    "金額",
                    ascending=False
                )
            )

            fig_project = px.bar(
                project_summary,
                x="專案名稱",
                y="金額",
                title="專案捐款金額比較"
            )

            st.plotly_chart(
                fig_project,
                width="stretch"
            )

        # -----------------------------
        # 接觸類型分析
        # -----------------------------

        st.subheader("📬 捐款者接觸分析")

        contact_summary = (
            contacts["接觸類型"]
            .value_counts()
            .reset_index()
        )

        contact_summary.columns = [
            "接觸類型",
            "接觸次數"
        ]

        fig_contact = px.bar(
            contact_summary,
            x="接觸類型",
            y="接觸次數",
            title="各類型接觸次數"
        )

        st.plotly_chart(
            fig_contact,
            width="stretch"
        )

        # -----------------------------
        # 捐款者分析
        # -----------------------------

        st.subheader("👥 捐款者分析")

        donor_summary = (
            donations
            .groupby("捐款人代碼")
            .agg(
                累計捐款金額=("金額", "sum"),
                捐款次數=("金額", "count"),
                最近捐款日期=("收到日期", "max")
            )
            .reset_index()
        )

        st.dataframe(
            donor_summary,
            width="stretch"
        )


# =====================================
# 5. AI 策略分析頁面
# =====================================

elif page == "AI 策略分析":

    st.header("🤖 AI 電子報策略分析")

    # -----------------------------
    # 檢查 API 設定
    # -----------------------------

    api_key = get_api_key()
    model_name = get_model()

    if api_key:
        st.success("✅ OpenAI API Key 已成功讀取")
    else:
        st.error(
            "❌ 找不到 OpenAI API Key。"
            "請檢查 .streamlit/secrets.toml。"
        )
        st.stop()

    required_keys = [
        "donors",
        "donations",
        "contacts"
    ]

    if not all(
        key in st.session_state
        for key in required_keys
    ):
        st.warning("請先上傳三份資料。")

    else:
        donors = st.session_state["donors"]
        donations = st.session_state["donations"]
        contacts = st.session_state["contacts"]

        # -----------------------------
        # 1. 捐款統計
        # -----------------------------

        summary = {
            "捐款人名單人數": int(
                donors["捐款人代碼"].nunique()
            ),
            "實際捐款人數": int(
                donations["捐款人代碼"].nunique()
            ),
            "捐款總金額": float(
                donations["金額"].sum()
            ),
            "捐款紀錄筆數": int(
                len(donations)
            ),
            "平均單筆捐款": (
                float(donations["金額"].mean())
                if len(donations) else 0
            ),
            "接觸紀錄筆數": int(
                len(contacts)
            ),
            "接觸人數": int(
                contacts["捐款人代碼"].nunique()
            )
        }

        # -----------------------------
        # 2. 每月捐款金額
        # -----------------------------

        monthly = (
            donations
            .assign(
                月份=donations["收到日期"]
                .dt.to_period("M")
                .astype(str)
            )
            .groupby("月份")["金額"]
            .sum()
        )

        summary["每月捐款金額"] = {
            str(k): float(v)
            for k, v in monthly.items()
        }

        # -----------------------------
        # 3. 專案分析
        # -----------------------------

        if "專案名稱" in donations.columns:

            project = (
                donations
                .groupby("專案名稱")["金額"]
                .sum()
            )

            summary["各專案捐款金額"] = {
                str(k): float(v)
                for k, v in project.items()
            }

        # -----------------------------
        # 4. 接觸類型分析
        # -----------------------------

        contact_types = (
            contacts["接觸類型"]
            .value_counts()
        )

        summary["各接觸類型次數"] = {
            str(k): int(v)
            for k, v in contact_types.items()
        }

        # -----------------------------
        # 5. 顯示分析摘要
        # -----------------------------

        st.subheader("📊 AI 分析資料摘要")

        with st.expander(
            "查看完整分析數據",
            expanded=False
        ):
            st.json(summary)

        st.write(
            "AI 將根據上述統計資料，"
            "產生電子報經營策略與建議。"
        )

        # -----------------------------
        # 6. AI 策略生成
        # -----------------------------

        if st.button(
            "✨ 生成 AI 電子報策略",
            type="primary"
        ):

            try:
                client = OpenAI(
                    api_key=api_key,
                    timeout=60.0
                )

                prompt = f"""
你是一位非營利組織的資深數據策略顧問。

你正在協助「微客公益行動協會」，
分析捐款者行為並制定電子報經營策略。

以下為實際計算出的彙總統計資料：

{summary}

請根據資料，產生具體且可執行的策略報告。

請依照以下結構撰寫：

## 1. Executive Summary
- 整體捐款表現
- 三個最重要的觀察
- 建議優先處理的問題

## 2. Key Insights
- 捐款金額與時間趨勢
- 不同專案的捐款表現
- 捐款者接觸類型分布
- 值得進一步分析的現象

## 3. Target Audience
- 建議優先經營的捐款者族群
- 每個族群的經營目標
- 分群需要的資料或條件
- 若尚未實際計算分群，請明確說明

## 4. Email Strategy
針對每個建議族群，提出：
- 電子報主題
- 核心溝通訊息
- CTA 行動呼籲
- 建議寄送頻率
- 建議追蹤指標

## 5. Recommended Actions
- 三個最優先執行的行動
- 執行順序
- 衡量成效的 KPI

重要限制：
1. 不得捏造任何數據。
2. 不得將相關性直接解讀為因果關係。
3. 不得宣稱已計算未提供的指標。
4. 區分數據事實、合理推論與待驗證假設。
5. 請使用繁體中文。
6. 建議需具體、可執行。
"""

                with st.spinner(
                    "🤖 AI 正在分析捐款數據，請稍候..."
                ):
                    response = client.responses.create(
                        model=model_name,
                        input=prompt
                    )

                report = response.output_text

                if not report:
                    raise ValueError(
                        "API 未回傳策略報告內容。"
                    )

                st.session_state["ai_report"] = report

                st.success(
                    "🎉 AI 電子報策略報告生成成功！"
                )

            except Exception as e:
                st.error(
                    f"AI 分析失敗：{e}"
                )

        # -----------------------------
        # 7. 顯示 AI 報告
        # -----------------------------

        if "ai_report" in st.session_state:

            st.divider()

            st.subheader(
                "📋 AI 電子報策略分析報告"
            )

            st.markdown(
                st.session_state["ai_report"]
            )

            st.download_button(
                label="📥 下載 AI 策略報告",
                data=st.session_state["ai_report"],
                file_name="micro_ai_strategy_report.md",
                mime="text/markdown"
            )
