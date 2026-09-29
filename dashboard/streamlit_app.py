import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

FASTAPI_BASE_URL = os.getenv(
    "FASTAPI_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

EXPERIMENT_DIRECTORY = PROJECT_ROOT / "storage" / "experiments"
RESULTS_PATH = EXPERIMENT_DIRECTORY / "experiment_results.json"
METRICS_PATH = EXPERIMENT_DIRECTORY / "metrics_summary.json"


st.set_page_config(
    page_title="MemPoisonGuard Dashboard",
    page_icon="🛡️",
    layout="wide",
)


def apply_custom_style() -> None:
    st.markdown(
        """
        <style>
            .main-title {
                color: #1F4E78;
                font-size: 2.2rem;
                font-weight: 700;
                margin-bottom: 0;
            }
            .sub-title {
                color: #5B9BD5;
                font-size: 1rem;
                margin-top: 0.2rem;
                margin-bottom: 1.5rem;
            }
            .security-note {
                background-color: #EAF4FB;
                border-left: 5px solid #5B9BD5;
                border-radius: 6px;
                padding: 0.8rem 1rem;
                margin-bottom: 1rem;
            }
            .safe-note {
                background-color: #E8F5E9;
                border-left: 5px solid #2E7D32;
                border-radius: 6px;
                padding: 0.8rem 1rem;
                margin-bottom: 1rem;
            }
            .danger-note {
                background-color: #FDECEC;
                border-left: 5px solid #C62828;
                border-radius: 6px;
                padding: 0.8rem 1rem;
                margin-bottom: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3)
def load_metrics() -> dict | None:
    if not METRICS_PATH.exists():
        return None

    with METRICS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(ttl=3)
def load_experiment_results() -> pd.DataFrame:
    if not RESULTS_PATH.exists():
        return pd.DataFrame()

    with RESULTS_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    return pd.DataFrame(records)


@st.cache_data(ttl=3)
def api_get(endpoint: str) -> dict:
    response = requests.get(
        f"{FASTAPI_BASE_URL}{endpoint}",
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=3)
def api_post(endpoint: str, payload: dict) -> dict:
    response = requests.post(
        f"{FASTAPI_BASE_URL}{endpoint}",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def status_color(status: str) -> str:
    mapping = {
        "verified_stored": "#2E7D32",
        "provisional": "#F9A825",
        "quarantined": "#C62828",
    }
    return mapping.get(status, "#5B9BD5")


def display_header() -> None:
    st.markdown(
        '<div class="main-title">🛡️ MemPoisonGuard Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="sub-title">'
            'Provenance-Aware Long-Term Memory Poisoning Defense '
            'for AI Agents'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_overview() -> None:
    st.header("Overview")

    metrics = load_metrics()

    if metrics is None:
        st.warning(
            "No experiment output found. Run POST /evaluation/run "
            "from FastAPI Swagger first."
        )
        return

    st.markdown(
        """
        <div class="security-note">
        <b>Controlled Evaluation:</b> Results below are generated from the
        currently saved local experiment output. They do not represent a
        universal security guarantee.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Scenarios",
        metrics["total_scenarios"],
    )
    col2.metric(
        "Malicious Inputs",
        metrics["malicious_scenarios"],
    )
    col3.metric(
        "Quarantined",
        metrics["guarded_quarantined_malicious"],
    )
    col4.metric(
        "Provisional",
        metrics["guarded_provisional_malicious"],
    )
    col5.metric(
        "Malicious Verified",
        metrics["guarded_verified_malicious"],
    )

    st.subheader("Detection Metrics")

    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = (
        st.columns(5)
    )

    metric_col1.metric(
        "Precision",
        f"{metrics['detection_precision']:.2%}",
    )
    metric_col2.metric(
        "Recall",
        f"{metrics['detection_recall']:.2%}",
    )
    metric_col3.metric(
        "F1 Score",
        f"{metrics['detection_f1']:.2%}",
    )
    metric_col4.metric(
        "False Positive Rate",
        f"{metrics['false_positive_rate']:.2%}",
    )
    metric_col5.metric(
        "False Negative Rate",
        f"{metrics['false_negative_rate']:.2%}",
    )

    left_col, right_col = st.columns(2)

    with left_col:
        chart_data = pd.DataFrame(
            {
                "Decision": [
                    "Quarantined",
                    "Provisional",
                    "Verified Malicious",
                ],
                "Count": [
                    metrics["guarded_quarantined_malicious"],
                    metrics["guarded_provisional_malicious"],
                    metrics["guarded_verified_malicious"],
                ],
            }
        )

        figure = px.bar(
            chart_data,
            x="Decision",
            y="Count",
            color="Decision",
            color_discrete_map={
                "Quarantined": "#C62828",
                "Provisional": "#F9A825",
                "Verified Malicious": "#2E7D32",
            },
            title="Guarded Decisions for Malicious Inputs",
            text="Count",
        )

        figure.update_layout(
            showlegend=False,
            yaxis_title="Scenario Count",
            xaxis_title="",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    with right_col:
        comparison_data = pd.DataFrame(
            {
                "System": [
                    "Baseline Agent",
                    "MemPoisonGuard",
                ],
                "Malicious Entries in Verified Memory": [
                    metrics["baseline_stored_malicious"],
                    metrics["guarded_verified_malicious"],
                ],
            }
        )

        figure = px.bar(
            comparison_data,
            x="System",
            y="Malicious Entries in Verified Memory",
            color="System",
            color_discrete_map={
                "Baseline Agent": "#C62828",
                "MemPoisonGuard": "#2E7D32",
            },
            title="Baseline vs Guarded Memory Exposure",
            text="Malicious Entries in Verified Memory",
        )

        figure.update_layout(
            showlegend=False,
            yaxis_title="Malicious Memory Entries",
            xaxis_title="",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    st.subheader("System Status")

    try:
        health = api_get("/health")

        status_col1, status_col2, status_col3 = st.columns(3)

        status_col1.success(
            f"API: {health['application']['status']}"
        )
        status_col2.success(
            f"Vector Store: {health['vector_store']['status']}"
        )

        ollama_status = health["ollama"]["status"]

        if ollama_status == "healthy":
            status_col3.success(
                f"Ollama: {ollama_status}"
            )
        else:
            status_col3.error(
                f"Ollama: {ollama_status}"
            )

    except requests.RequestException as error:
        st.error(
            f"Could not connect to FastAPI at {FASTAPI_BASE_URL}. "
            f"Start the backend first. Details: {error}"
        )


def render_evaluation_results() -> None:
    st.header("Evaluation Results")

    results = load_experiment_results()

    if results.empty:
        st.warning(
            "No saved experiment results found. Run the evaluation first."
        )
        return

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    label_filter = filter_col1.multiselect(
        "Filter by Label",
        options=sorted(results["label"].dropna().unique()),
        default=sorted(results["label"].dropna().unique()),
    )

    status_filter = filter_col2.multiselect(
        "Filter by Guarded Status",
        options=sorted(
            results["guarded_storage_status"].dropna().unique()
        ),
        default=sorted(
            results["guarded_storage_status"].dropna().unique()
        ),
    )

    category_filter = filter_col3.multiselect(
        "Filter by Category",
        options=sorted(results["category"].dropna().unique()),
        default=sorted(results["category"].dropna().unique()),
    )

    filtered_results = results[
        results["label"].isin(label_filter)
        & results["guarded_storage_status"].isin(status_filter)
        & results["category"].isin(category_filter)
    ].copy()

    st.subheader("Scenario-Level Results")

    display_columns = [
        "scenario_id",
        "category",
        "label",
        "baseline_storage_status",
        "guarded_storage_status",
        "guarded_injection_score",
        "guarded_contradiction_score",
        "guarded_trust_score",
        "guarded_risk_score",
        "guarded_detector_flags",
        "guarded_quarantine_reason",
    ]

    st.dataframe(
        filtered_results[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Storage Decision Distribution")

    decision_data = (
        filtered_results.groupby(
            ["label", "guarded_storage_status"]
        )
        .size()
        .reset_index(name="count")
    )

    figure = px.bar(
        decision_data,
        x="label",
        y="count",
        color="guarded_storage_status",
        barmode="group",
        color_discrete_map={
            "verified_stored": "#2E7D32",
            "provisional": "#F9A825",
            "quarantined": "#C62828",
        },
        title="Guarded Storage Decisions by Scenario Label",
        text="count",
    )

    figure.update_layout(
        xaxis_title="Scenario Label",
        yaxis_title="Scenario Count",
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )

    st.subheader("Baseline vs Guarded Storage")

    comparison = filtered_results[
        [
            "scenario_id",
            "label",
            "baseline_storage_status",
            "guarded_storage_status",
        ]
    ].copy()

    st.dataframe(
        comparison,
        use_container_width=True,
        hide_index=True,
    )

    csv_output = filtered_results.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Filtered Results as CSV",
        data=csv_output,
        file_name="mempoisonguard_filtered_evaluation_results.csv",
        mime="text/csv",
    )


def render_memory_explorer() -> None:
    st.header("Memory Explorer")

    try:
        response = api_get("/guarded/memories")
        memories = response.get("memories", [])

    except requests.RequestException as error:
        st.error(
            f"Could not load guarded memories. Details: {error}"
        )
        return

    if not memories:
        st.info("No guarded memory records are available.")
        return

    memory_df = pd.DataFrame(memories)

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    available_statuses = sorted(
        memory_df["storage_status"].dropna().unique()
    )

    selected_statuses = filter_col1.multiselect(
        "Memory Status",
        options=available_statuses,
        default=available_statuses,
    )

    source_types = sorted(
        memory_df["source_type"].dropna().unique()
    )

    selected_sources = filter_col2.multiselect(
        "Source Type",
        options=source_types,
        default=source_types,
    )

    minimum_trust = filter_col3.slider(
        "Minimum Trust Score",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
    )

    filtered_memory_df = memory_df[
        memory_df["storage_status"].isin(selected_statuses)
        & memory_df["source_type"].isin(selected_sources)
        & (memory_df["trust_score"] >= minimum_trust)
    ].copy()

    display_columns = [
        "memory_id",
        "content",
        "source_type",
        "source_name",
        "provenance_score",
        "trust_score",
        "risk_score",
        "injection_score",
        "contradiction_score",
        "verification_status",
        "storage_status",
        "created_at",
    ]

    st.dataframe(
        filtered_memory_df[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Trust vs Risk Distribution")

    figure = px.scatter(
        filtered_memory_df,
        x="trust_score",
        y="risk_score",
        color="storage_status",
        hover_data=[
            "memory_id",
            "source_type",
            "source_name",
        ],
        color_discrete_map={
            "verified_stored": "#2E7D32",
            "provisional": "#F9A825",
            "quarantined": "#C62828",
        },
        title="Memory Trust-Risk Distribution",
    )

    figure.update_layout(
        xaxis_title="Trust Score",
        yaxis_title="Risk Score",
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )


def render_quarantine_review() -> None:
    st.header("Quarantine Review")

    try:
        response = api_get("/guarded/quarantine")
        memories = response.get("memories", [])

    except requests.RequestException as error:
        st.error(
            f"Could not load quarantined records. Details: {error}"
        )
        return

    if not memories:
        st.success("No quarantined memory records found.")
        return

    st.markdown(
        """
        <div class="danger-note">
        <b>Quarantine policy:</b> These records are retained as audit
        evidence but are excluded from safe guarded-memory retrieval.
        </div>
        """,
        unsafe_allow_html=True,
    )

    for memory in memories:
        title = (
            f"{memory['memory_id']} — "
            f"{memory['source_type']} — "
            f"Risk: {memory['risk_score']:.3f}"
        )

        with st.expander(title):
            st.markdown("**Candidate Content**")
            st.code(memory["content"], language=None)

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Trust Score",
                f"{memory['trust_score']:.3f}",
            )
            col2.metric(
                "Risk Score",
                f"{memory['risk_score']:.3f}",
            )
            col3.metric(
                "Injection Score",
                f"{memory['injection_score']:.3f}",
            )
            col4.metric(
                "Contradiction Score",
                f"{memory['contradiction_score']:.3f}",
            )

            st.markdown("**Detector Flags**")
            st.write(memory["detector_flags"])

            st.markdown("**Quarantine Reason**")
            st.warning(
                memory["quarantine_reason"]
                or "No explicit quarantine reason recorded."
            )

            st.markdown("**Provenance**")
            st.json(
                {
                    "source_type": memory["source_type"],
                    "source_name": memory["source_name"],
                    "source_reference": memory["source_reference"],
                    "content_hash": memory["content_hash"],
                    "created_at": memory["created_at"],
                }
            )

            st.markdown("**Analysis Evidence**")
            st.json(memory["analysis_evidence"])


def render_guarded_chat() -> None:
    st.header("Guarded Chat")

    st.markdown(
        """
        <div class="safe-note">
        <b>Safe retrieval rule:</b> Only verified memories are eligible
        for retrieval. Provisional and quarantined records are excluded.
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_question = (
        "What technologies are used in MemPoisonGuard?"
    )

    question = st.text_area(
        "Ask MemPoisonGuard",
        value=default_question,
        height=100,
    )

    top_k = st.slider(
        "Verified memories to retrieve",
        min_value=1,
        max_value=10,
        value=5,
    )

    if st.button("Send to Guarded Agent", type="primary"):
        if not question.strip():
            st.warning("Enter a question before sending.")
            return

        with st.spinner(
            "Retrieving verified memory and generating a safe response..."
        ):
            try:
                response = api_post(
                    "/guarded/chat",
                    {
                        "message": question.strip(),
                        "top_k": top_k,
                    },
                )

            except requests.RequestException as error:
                st.error(
                    f"Guarded chat request failed. Details: {error}"
                )
                return

        st.subheader("Guarded Agent Response")
        st.write(response["answer"])

        st.caption(
            f"Model: {response['model']}"
        )

        st.info(response["security_notice"])

        st.subheader("Safe Retrieval Trace")

        retrieved_memories = response.get(
            "retrieved_memories",
            [],
        )

        if not retrieved_memories:
            st.info("No verified memory was relevant to this question.")
            return

        retrieval_df = pd.DataFrame(retrieved_memories)

        st.dataframe(
            retrieval_df[
                [
                    "memory_id",
                    "content",
                    "source_type",
                    "source_name",
                    "trust_score",
                    "risk_score",
                    "semantic_distance",
                    "relevance_score",
                    "safe_retrieval_score",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        figure = px.bar(
            retrieval_df,
            x="memory_id",
            y="safe_retrieval_score",
            color="safe_retrieval_score",
            color_continuous_scale="Blues",
            hover_data=[
                "trust_score",
                "risk_score",
                "relevance_score",
            ],
            title="Safe Retrieval Ranking",
        )

        figure.update_layout(
            xaxis_title="Memory ID",
            yaxis_title="Safe Retrieval Score",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )


def main() -> None:
    apply_custom_style()
    display_header()

    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Select Dashboard Page",
        options=[
            "Overview",
            "Evaluation Results",
            "Memory Explorer",
            "Quarantine Review",
            "Guarded Chat",
        ],
    )

    st.sidebar.divider()

    st.sidebar.caption(
        f"FastAPI Backend: {FASTAPI_BASE_URL}"
    )

    if st.sidebar.button("Refresh Dashboard Data"):
        st.cache_data.clear()
        st.rerun()

    if page == "Overview":
        render_overview()

    elif page == "Evaluation Results":
        render_evaluation_results()

    elif page == "Memory Explorer":
        render_memory_explorer()

    elif page == "Quarantine Review":
        render_quarantine_review()

    elif page == "Guarded Chat":
        render_guarded_chat()


if __name__ == "__main__":
    main()