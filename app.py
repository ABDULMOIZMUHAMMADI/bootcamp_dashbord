import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_URL = "http://localhost:8000"

BOOTCAMPS = {
    "Bootcamp 4.0": "69c538969d2f7dcce6f2df20",
    "Bootcamp 3.0": "69c63a4736adc54470ff7703",
    "Bootcamp 2.0": "69c63a5336adc54470ff7704",
}

DOMAINS = {
    "Web Development": "69c538969d2f7dcce6f2df24",
    "AI Engineering":  "69c538969d2f7dcce6f2df26",
    "UI UX":           "69c53f3b0b619312a3c67d7c",
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get(path):
    try:
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "⚠️ Cannot reach API. Make sure FastAPI is running on localhost:8000"
    except Exception as e:
        try:
            return None, r.json().get("detail", str(e))
        except Exception:
            return None, str(e)

def post(path, payload):
    try:
        r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=30)
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.exceptions.ConnectionError:
        return None, "⚠️ Cannot reach API."
    except Exception as e:
        return None, str(e)

def err(msg):
    st.error(f"**Error:** {msg}")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Bootcamp Tracker",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #1f2937;
}
[data-testid="stSidebar"] * { color: #d1d5db !important; }
[data-testid="stSidebar"] h2 { color: #f9fafb !important; font-size: 1.1rem !important; }

/* ── metrics ── */
[data-testid="metric-container"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
}
[data-testid="metric-container"] label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b !important;
    font-weight: 600;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    color: #0f172a;
}

/* ── buttons ── */
.stButton > button {
    background: #0f172a;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.5rem 1.3rem;
    transition: background 0.2s;
}
.stButton > button:hover { background: #1e293b; }

/* ── form inputs ── */
.stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #475569;
}

/* ── headers ── */
h1 { font-weight: 700; font-size: 1.6rem !important; color: #0f172a; }
h2 { font-weight: 700; font-size: 1.15rem !important; color: #1e293b;
     border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 1.4rem; }
h3 { font-weight: 600; font-size: 1rem !important; color: #334155; }

/* ── notification badge ── */
.notif-badge {
    display: inline-block;
    background: #ef4444;
    color: white;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 1px 7px;
    margin-left: 6px;
    vertical-align: middle;
}

/* ── card ── */
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.card:hover { border-color: #94a3b8; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.card .title { font-weight: 600; font-size: 0.95rem; margin-bottom: 4px; }
.card .meta  { font-size: 0.78rem; color: #64748b; font-family: 'JetBrains Mono', monospace; }

/* ── chips ── */
.chip { display:inline-block; border-radius:4px; font-size:0.7rem; font-weight:600;
        padding:2px 8px; margin:2px 3px 2px 0; letter-spacing:0.03em; }
.chip-green  { background:#dcfce7; color:#166534; border:1px solid #86efac; }
.chip-red    { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; }
.chip-blue   { background:#dbeafe; color:#1d4ed8; border:1px solid #93c5fd; }
.chip-gray   { background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; }
.chip-orange { background:#ffedd5; color:#9a3412; border:1px solid #fdba74; }

/* ── panel switcher ── */
.panel-btn {
    display: inline-block; padding: 8px 24px; border-radius: 6px;
    font-weight: 700; font-size: 0.9rem; cursor: pointer;
    text-align: center; transition: all 0.2s;
}

/* ── notification box ── */
.notif-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.82rem;
}
.notif-box-student {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.82rem;
}
.notif-title { font-weight: 700; font-size: 0.75rem; text-transform: uppercase;
               letter-spacing: 0.08em; margin-bottom: 3px; }

hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# SESSION STATE – panel switch
# ═══════════════════════════════════════════════
if "panel" not in st.session_state:
    st.session_state.panel = "Admin"

# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
with top_col1:
    st.markdown("#  Bootcamp Tracker")
with top_col2:
    if st.button("Admin Panel", use_container_width=True):
        st.session_state.panel = "Admin"
with top_col3:
    if st.button(" Student Panel", use_container_width=True):
        st.session_state.panel = "Student"

st.markdown(f"**Active Panel:** `{st.session_state.panel}`")
st.markdown("---")

panel = st.session_state.panel

# ═══════════════════════════════════════════════
# ██████████  ADMIN PANEL  ██████████
# ═══════════════════════════════════════════════
if panel == "Admin":

    with st.sidebar:
        st.markdown("##  Admin")
        st.markdown("---")
        admin_page = st.radio("Section", [
            " Dashboard",
            " Bootcamp Details",
            " Domain Details",
            " Student Details",
            " Assignments",
            " All Submissions",
            " Search Student",
            " Notifications",
        ], label_visibility="collapsed")

    # ───────────────────────────────────────────
    # NOTIFICATION BAR (admin)
    # ───────────────────────────────────────────
    notif_data, _ = get("/notifications/admin")
    notif_count = notif_data.get("count", 0) if notif_data else 0

    if notif_count > 0:
        with st.expander(f" Notifications  ({notif_count} unread)", expanded=False):
            for n in (notif_data.get("data", []))[:10]:
                msg  = n.get("message", "")
                roll = n.get("studentRollNo", "")
                dom  = n.get("domainName", "")
                asgn = n.get("assignmentTitle", "Assignment")
                ts   = n.get("createdAt", {})
                if isinstance(ts, dict): ts = ts.get("$date", "")
                st.markdown(f"""<div class='notif-box'>
                    <div class='notif-title'> Missed Submission</div>
                    {msg}<br>
                    <span class='chip chip-gray'>Roll #{roll}</span>
                    <span class='chip chip-blue'>{dom}</span>
                    <span class='chip chip-orange'>{asgn}</span>
                    <span style='font-size:0.7rem;color:#94a3b8;'>{str(ts)[:19]}</span>
                </div>""", unsafe_allow_html=True)
        st.markdown("")

    # ──────────────────────────────────────────
    # DASHBOARD
    # ──────────────────────────────────────────
    if admin_page == " Dashboard":
        st.markdown("## Dashboard")

        # KPIs
        cnt, _ = get("/students/count")
        asgn_all, _ = get("/assignments/all")
        subs_all, _ = get("/assignments/submissions/all")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Students", cnt.get("total_students", 0) if cnt else "—")
        c2.metric("Bootcamps",      len(BOOTCAMPS))
        c3.metric("Active Assignments", asgn_all.get("count", 0) if asgn_all else "—")
        c4.metric("Total Submissions",  subs_all.get("count", 0) if subs_all else "—")

        st.markdown("---")
        # Bootcamp overview chart
        overview, ov_err = get("/admin/bootcamp-overview")
        if ov_err:
            err(ov_err)
        else:
            rows = []
            for bc in overview.get("bootcamps", []):
                for dom in bc.get("domains", []):
                    rows.append({
                        "Bootcamp": bc["bootcamp_name"],
                        "Domain":   dom["domain_name"],
                        "Students": dom["student_count"],
                        "Submitted Students": dom["submitted_students"],
                        "Not Submitted":      dom["not_submitted_students"],
                        "Assignments":        dom["total_assignments"],
                    })
            df = pd.DataFrame(rows)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Students per Domain (all bootcamps)")
                fig = px.bar(df.groupby("Domain")["Students"].sum().reset_index(),
                             x="Domain", y="Students",
                             color="Domain",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Submission Rate per Domain")
                sub_df = df.groupby("Domain")[["Submitted Students","Not Submitted"]].sum().reset_index()
                fig2 = px.bar(sub_df, x="Domain",
                              y=["Submitted Students", "Not Submitted"],
                              barmode="stack",
                              color_discrete_map={"Submitted Students": "#22c55e", "Not Submitted": "#ef4444"})
                fig2.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig2, use_container_width=True)

            st.markdown("### Students per Bootcamp")
            bc_df = df.groupby("Bootcamp")["Students"].sum().reset_index()
            fig3 = px.pie(bc_df, names="Bootcamp", values="Students",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig3.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig3, use_container_width=True)

    # ──────────────────────────────────────────
    # BOOTCAMP DETAILS
    # ──────────────────────────────────────────
    elif admin_page == " Bootcamp Details":
        st.markdown("## Bootcamp Details")

        selected_bc = st.selectbox("Select Bootcamp", list(BOOTCAMPS.keys()))
        bid = BOOTCAMPS[selected_bc]

        if st.button("Load Details"):
            # overview for this bootcamp
            overview, ov_err = get("/admin/bootcamp-overview")
            stats, st_err   = get(f"/stats/bootcamp/{bid}")

            if ov_err: err(ov_err)
            else:
                # find this bootcamp in overview
                bc_data = next((b for b in overview["bootcamps"] if b["bootcamp_id"] == bid), None)

                if bc_data:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Students", bc_data["total_students"])
                    c2.metric("Domains", len(bc_data["domains"]))
                    total_asgn = sum(d["total_assignments"] for d in bc_data["domains"])
                    c3.metric("Active Assignments", total_asgn)

                    st.markdown("### Domain Breakdown")
                    for dom in bc_data["domains"]:
                        with st.expander(f" {dom['domain_name']}  —  {dom['student_count']} students"):
                            dc1, dc2, dc3, dc4 = st.columns(4)
                            dc1.metric("Students", dom["student_count"])
                            dc2.metric("Assignments", dom["total_assignments"])
                            dc3.metric("Submitted (students)", dom["submitted_students"])
                            dc4.metric("Not Submitted", dom["not_submitted_students"])

                            # bar chart for this domain
                            fig = go.Figure(go.Bar(
                                x=["Submitted", "Not Submitted"],
                                y=[dom["submitted_students"], dom["not_submitted_students"]],
                                marker_color=["#22c55e", "#ef4444"]
                            ))
                            fig.update_layout(height=220, margin=dict(t=10, b=10))
                            st.plotly_chart(fig, use_container_width=True)

                            # show students button
                            if st.button(f"View Students — {dom['domain_name']}", key=f"vs_{dom['domain_id']}"):
                                students_d, s_err = get(f"/students/domain/{dom['domain_id']}")
                                if s_err: err(s_err)
                                else:
                                    slist = students_d.get("data", [])
                                    # filter by bootcamp
                                    slist = [s for s in slist if s.get("studentBootcampId") == bid]
                                    for s in slist[:50]:
                                        st.markdown(
                                            f"<div class='card'><div class='title'>{s.get('name')} "
                                            f"<span class='chip chip-gray'>Roll #{s.get('rollNo')}</span></div>"
                                            f"<div class='meta'>{s.get('email')} | 📍 {s.get('location')}</div></div>",
                                            unsafe_allow_html=True
                                        )

                    # chart: students per domain in this bootcamp
                    dom_names = [d["domain_name"] for d in bc_data["domains"]]
                    dom_counts = [d["student_count"] for d in bc_data["domains"]]
                    fig4 = px.bar(x=dom_names, y=dom_counts, labels={"x": "Domain", "y": "Students"},
                                  color=dom_names, color_discrete_sequence=px.colors.qualitative.Vivid)
                    fig4.update_layout(showlegend=False, margin=dict(t=10, b=10), height=280)
                    st.plotly_chart(fig4, use_container_width=True)

    # ──────────────────────────────────────────
    # DOMAIN DETAILS
    # ──────────────────────────────────────────
    elif admin_page == " Domain Details":
        st.markdown("## Domain Details")

        selected_dom = st.selectbox("Select Domain", list(DOMAINS.keys()))
        did = DOMAINS[selected_dom]

        if st.button("Load Domain Stats"):
            data, de = get(f"/stats/domain/{did}")
            if de: err(de)
            else:
                st.metric("Total Students", data["total_students"])
                st.markdown("### Per Bootcamp")
                rows = []
                for b in data.get("bootcamps", []):
                    rows.append({"Bootcamp": b.get("bootcampName", b["_id"]), "Students": b["count"]})
                if rows:
                    df = pd.DataFrame(rows)
                    fig = px.bar(df, x="Bootcamp", y="Students",
                                 color="Bootcamp",
                                 color_discrete_sequence=px.colors.qualitative.Pastel1)
                    fig.update_layout(showlegend=False, margin=dict(t=10,b=10), height=280)
                    st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### Assignments in Domain")
        if st.button("Load Assignments"):
            asgn, ae = get(f"/assignments/domain/{did}")
            if ae: err(ae)
            else:
                st.markdown(f"**{asgn['count']} active assignments**")
                for a in asgn.get("data", []):
                    aid = a.get("_id", {})
                    if isinstance(aid, dict): aid = aid.get("$oid", "")
                    title = a.get("title", "Untitled")
                    deadline = a.get("deadline", "")
                    if isinstance(deadline, dict): deadline = deadline.get("$date", "")
                    st.markdown(
                        f"<div class='card'><div class='title'>{title}</div>"
                        f"<div class='meta'>ID: {aid} | Deadline: {str(deadline)[:10]}</div></div>",
                        unsafe_allow_html=True
                    )

    # ──────────────────────────────────────────
    # STUDENT DETAILS
    # ──────────────────────────────────────────
    elif admin_page == "👩‍💻 Student Details":
        st.markdown("## Student Details")

        filter_by = st.radio("Filter students by", ["Bootcamp", "Domain"], horizontal=True)
        if filter_by == "Bootcamp":
            sel = st.selectbox("Bootcamp", list(BOOTCAMPS.keys()))
            endpoint = f"/students/bootcamp/{BOOTCAMPS[sel]}"
        else:
            sel = st.selectbox("Domain", list(DOMAINS.keys()))
            endpoint = f"/students/domain/{DOMAINS[sel]}"

        if st.button("Load Students"):
            data, de = get(endpoint)
            if de: err(de)
            else:
                students = data.get("data", [])
                st.metric("Students Found", len(students))

                search = st.text_input("🔎 Filter by name or roll no")
                if search:
                    students = [s for s in students
                                if search.lower() in str(s.get("name","")).lower()
                                or search in str(s.get("rollNo",""))]

                for s in students[:100]:
                    status = s.get("studentStatus", "")
                    chip = "chip-green" if status == "enrolled" else "chip-red"
                    domain_name = next((k for k,v in DOMAINS.items() if v == s.get("domainId","")), s.get("domainId",""))
                    bc_name     = next((k for k,v in BOOTCAMPS.items() if v == s.get("studentBootcampId","")), s.get("studentBootcampId",""))
                    st.markdown(
                        f"<div class='card'>"
                        f"<div class='title'>{s.get('name')} "
                        f"<span class='chip chip-gray'>Roll #{s.get('rollNo')}</span> "
                        f"<span class='chip {chip}'>{status}</span></div>"
                        f"<div class='meta'>{s.get('email')} | 📍 {s.get('location')} | "
                        f"<span class='chip chip-blue'>{domain_name}</span> "
                        f"<span class='chip chip-gray'>{bc_name}</span></div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                if len(students) > 100:
                    st.caption(f"Showing first 100 of {len(students)} students.")

    # ──────────────────────────────────────────
    # ASSIGNMENTS
    # ──────────────────────────────────────────
    elif admin_page == "📝 Assignments":
        st.markdown("## Assignments")

        tab1, tab2, tab3 = st.tabs(["All Assignments", "Search by Name", "Assignment Detail"])

        with tab1:
            if st.button("Load All Assignments"):
                data, ae = get("/assignments/all")
                if ae: err(ae)
                else:
                    st.metric("Total Active Assignments", data["count"])
                    for a in data.get("data", []):
                        aid = a.get("_id", {})
                        if isinstance(aid, dict): aid = aid.get("$oid", "")
                        title    = a.get("title", "Untitled")
                        deadline = a.get("deadline", "")
                        if isinstance(deadline, dict): deadline = deadline.get("$date","")
                        domain   = a.get("domain", "")
                        dname    = next((k for k,v in DOMAINS.items() if v==domain), domain)
                        st.markdown(
                            f"<div class='card'><div class='title'>{title}</div>"
                            f"<div class='meta'>ID: {aid} | "
                            f"<span class='chip chip-blue'>{dname}</span> | "
                            f"Deadline: {str(deadline)[:10]}</div></div>",
                            unsafe_allow_html=True
                        )

        with tab2:
            name = st.text_input("Assignment Name / Keyword")
            if st.button("Search") and name:
                data, ae = get(f"/assignments/by-name/{name}")
                if ae: err(ae)
                else:
                    for a in data.get("data", []):
                        aid = a.get("_id", {})
                        if isinstance(aid, dict): aid = aid.get("$oid","")
                        st.markdown(
                            f"<div class='card'><div class='title'>{a.get('title','Untitled')}</div>"
                            f"<div class='meta'>ID: {aid}</div></div>",
                            unsafe_allow_html=True
                        )

        with tab3:
            aid_input = st.text_input("Assignment ObjectId")
            if st.button("Get Detail") and aid_input:
                data, ae = get(f"/assignments/detail/{aid_input.strip()}")
                if ae: err(ae)
                else:
                    st.markdown(f"### {data.get('title', 'Assignment')}")
                    st.json(data)

                    # submissions for this assignment
                    subs, se = get(f"/assignments/submissions/by-assignment/{aid_input.strip()}")
                    if not se and subs:
                        st.markdown(f"**{subs['count']} submissions**")
                        rows = []
                        for s in subs.get("data", []):
                            rows.append({
                                "Roll No":       s.get("rollNo") or s.get("studentRollNo",""),
                                "Student":       s.get("studentName",""),
                                "Status":        s.get("status",""),
                                "Submitted At":  str(s.get("submittedAt",""))[:19],
                                "URL":           s.get("URL",""),
                            })
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ──────────────────────────────────────────
    # ALL SUBMISSIONS
    # ──────────────────────────────────────────
    elif admin_page == "📬 All Submissions":
        st.markdown("## All Submissions")

        if st.button("Load All Submissions"):
            data, de = get("/assignments/submissions/all")
            if de: err(de)
            else:
                st.metric("Total Submissions", data["count"])
                subs = data.get("data", [])
                rows = []
                for s in subs:
                    rows.append({
                        "Roll No":       s.get("studentRollNo",""),
                        "Student":       s.get("studentName",""),
                        "Bootcamp":      s.get("bootcampName",""),
                        "Domain":        s.get("domainName",""),
                        "Assignment":    s.get("assignmentTitle",""),
                        "Status":        s.get("status",""),
                        "Submitted At":  str(s.get("submittedAt",""))[:19],
                        "URL":           s.get("URL",""),
                    })
                if rows:
                    df = pd.DataFrame(rows)

                    # filter
                    col1, col2 = st.columns(2)
                    bc_filter  = col1.selectbox("Filter Bootcamp", ["All"] + list(BOOTCAMPS.keys()))
                    dom_filter = col2.selectbox("Filter Domain",   ["All"] + list(DOMAINS.keys()))
                    if bc_filter != "All":
                        df = df[df["Bootcamp"] == bc_filter]
                    if dom_filter != "All":
                        df = df[df["Domain"] == dom_filter]

                    st.dataframe(df, use_container_width=True)

                    # chart
                    if not df.empty:
                        st.markdown("### Submissions by Domain")
                        fig = px.histogram(df, x="Domain", color="Domain",
                                           color_discrete_sequence=px.colors.qualitative.Safe)
                        fig.update_layout(showlegend=False, margin=dict(t=10,b=10))
                        st.plotly_chart(fig, use_container_width=True)

    # ──────────────────────────────────────────
    # SEARCH STUDENT
    # ──────────────────────────────────────────
    elif admin_page == " Search Student":
        st.markdown("## Search Student")

        search_type = st.radio("Search by", ["Roll Number", "ObjectId"], horizontal=True)
        inp = st.text_input("Enter value")

        col1, col2 = st.columns(2)
        search_clicked = col1.button("Get Student Info")
        subs_clicked   = col2.button("Get Submission Summary")

        if inp.strip():
            param = f"roll_no={inp.strip()}" if search_type == "Roll Number" else f"student_id={inp.strip()}"

            if search_clicked:
                data, de = get(f"/search/student?{param}")
                if de: err(de)
                else:
                    s = data
                    c1, c2 = st.columns([1,3])
                    with c1:
                        av = s.get("avatar","")
                        if av: st.image(av, width=90)
                    with c2:
                        st.markdown(f"### {s.get('name')}")
                        st.markdown(
                            f"<span class='chip chip-blue'>{s.get('domainName','')}</span> "
                            f"<span class='chip chip-gray'>{s.get('bootcampName','')}</span> "
                            f"<span class='chip chip-green'>{s.get('studentStatus','')}</span>",
                            unsafe_allow_html=True
                        )
                    st.markdown("---")
                    r1,r2,r3 = st.columns(3)
                    r1.markdown(f"**Roll No**\n\n{s.get('rollNo','—')}")
                    r2.markdown(f"**Email**\n\n{s.get('email','—')}")
                    r3.markdown(f"**Location**\n\n{s.get('location','—')}")
                    st.markdown(f"**Teacher ID:** `{s.get('teacherId','—')}`  **Teacher:** {s.get('teacherName','—')}")

            if subs_clicked:
                data, de = get(f"/search/student-submissions?{param}")
                if de: err(de)
                else:
                    st.markdown(f"### {data['student_name']}  (Roll #{data['roll_no']})")
                    m1,m2,m3 = st.columns(3)
                    m1.metric("Total Assignments", data["total_assignments"])
                    m2.metric("Submitted",         data["submitted_count"])
                    m3.metric("Remaining",         data["remaining_count"])

                    # donut chart
                    fig = go.Figure(go.Pie(
                        labels=["Submitted", "Remaining"],
                        values=[data["submitted_count"], max(data["remaining_count"],0)],
                        hole=0.55,
                        marker_colors=["#22c55e", "#f1f5f9"]
                    ))
                    fig.update_layout(margin=dict(t=10,b=10), height=220, showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)

                    if data.get("submitted"):
                        st.markdown("#### Submitted Assignments")
                        rows = [{"Title": s["title"], "Submitted At": s["submittedAt"][:19], "URL": s["url"]}
                                for s in data["submitted"]]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ──────────────────────────────────────────
    # NOTIFICATIONS (full page)
    # ──────────────────────────────────────────
    elif admin_page == " Notifications":
        st.markdown("## Notifications")

        col1, col2 = st.columns([2,1])
        with col2:
            if st.button("🔄 Run Missed-Assignment Check"):
                with st.spinner("Scanning…"):
                    res, re = get("/check-missed-assignments")
                if re: err(re)
                else:
                    st.success(f"Generated {res['total_notifications']} new notifications")

        data, de = get("/notifications/admin")
        if de: err(de)
        else:
            st.metric("Total Notifications", data["count"])
            notifs = data.get("data", [])
            if not notifs:
                st.info("No notifications yet. Run the missed-assignment check above.")
            else:
                # chart: per domain
                dom_counts = {}
                for n in notifs:
                    d = n.get("domainName","Unknown")
                    dom_counts[d] = dom_counts.get(d, 0) + 1
                fig = px.bar(x=list(dom_counts.keys()), y=list(dom_counts.values()),
                             labels={"x":"Domain","y":"Missed Submissions"},
                             color=list(dom_counts.keys()),
                             color_discrete_sequence=px.colors.qualitative.Antique)
                fig.update_layout(showlegend=False, margin=dict(t=10,b=10), height=260)
                st.plotly_chart(fig, use_container_width=True)

                for n in notifs:
                    msg  = n.get("message","")
                    roll = n.get("studentRollNo","")
                    dom  = n.get("domainName","")
                    asgn = n.get("assignmentTitle","")
                    ts   = n.get("createdAt",{})
                    if isinstance(ts, dict): ts = ts.get("$date","")
                    st.markdown(
                        f"<div class='notif-box'>"
                        f"<div class='notif-title'> Missed Submission</div>"
                        f"{msg}<br>"
                        f"<span class='chip chip-gray'>Roll #{roll}</span>"
                        f"<span class='chip chip-blue'>{dom}</span>"
                        f"<span class='chip chip-orange'>{asgn}</span>"
                        f"<span style='font-size:0.7rem;color:#94a3b8;float:right'>{str(ts)[:19]}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )


# ═══════════════════════════════════════════════
# ██████████  STUDENT PANEL  ██████████
# ═══════════════════════════════════════════════
elif panel == "Student":

    with st.sidebar:
        st.markdown("##  Student")
        st.markdown("---")
        student_page = st.radio("Section", [
            " My Dashboard",
            " Submit Assignment",
            " My Notifications",
        ], label_visibility="collapsed")

    # ── roll number input (persistent)
    st.markdown("### Enter Your Roll Number")
    roll_input = st.number_input("Roll Number", min_value=1, step=1, value=st.session_state.get("student_roll", 2000))
    if st.button("Load My Data"):
        st.session_state["student_roll"] = int(roll_input)
        st.session_state["student_data"] = None  # reset cache

    roll_no = st.session_state.get("student_roll", None)

    # Load student panel data
    if roll_no and "student_data" not in st.session_state:
        data, de = get(f"/student/panel/{roll_no}")
        if de:
            err(de)
        else:
            st.session_state["student_data"] = data

    if roll_no:
        sdata = st.session_state.get("student_data")
        if not sdata:
            data, de = get(f"/student/panel/{roll_no}")
            if de:
                err(de)
                st.stop()
            sdata = data
            st.session_state["student_data"] = sdata

        student = sdata.get("student", {})

        # ── notification bar for student
        student_notifs = sdata.get("notifications", [])
        if student_notifs:
            with st.expander(f" You have {len(student_notifs)} notification(s)", expanded=False):
                for n in student_notifs:
                    msg = n.get("message","")
                    asgn = n.get("assignmentTitle", "an assignment")
                    ts = n.get("createdAt",{})
                    if isinstance(ts,dict): ts=ts.get("$date","")
                    st.markdown(
                        f"<div class='notif-box-student'>"
                        f"<div class='notif-title'>📋 Reminder from Admin</div>"
                        f"You have not submitted <b>{asgn}</b>. Please submit before the deadline.<br>"
                        f"<span style='font-size:0.7rem;color:#94a3b8;'>{str(ts)[:19]}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        st.markdown("---")

        # ─────────────────────────────────────────
        # MY DASHBOARD
        # ─────────────────────────────────────────
        if student_page == " My Dashboard":
            st.markdown("## My Dashboard")

            # profile header
            c1, c2 = st.columns([1, 4])
            with c1:
                av = student.get("avatar","")
                if av: st.image(av, width=85)
            with c2:
                st.markdown(f"### {student.get('name','')}")
                st.markdown(
                    f"<span class='chip chip-gray'>Roll #{student.get('rollNo')}</span>"
                    f"<span class='chip chip-blue'>{student.get('domainName','')}</span>"
                    f"<span class='chip chip-gray'>{student.get('bootcampName','')}</span>"
                    f"<span class='chip chip-green'>{student.get('studentStatus','')}</span>",
                    unsafe_allow_html=True
                )
            st.markdown("---")

            # key details
            r1, r2, r3 = st.columns(3)
            r1.markdown(f"**Email**\n\n{student.get('email','—')}")
            r2.markdown(f"**Location**\n\n{student.get('location','—')}")
            r3.markdown(f"**Phone**\n\n{student.get('phone','—')}")

            teacher_name = student.get("teacherName","")
            teacher_id   = student.get("teacherId","")
            st.markdown(f"**Teacher:** {teacher_name}  `{teacher_id}`")
            st.markdown(f"**Bio:** {student.get('bio','—')}")

            st.markdown("---")

            # assignment metrics
            total_asgn = sdata.get("total_assignments", 0)
            submitted  = sdata.get("submitted_count", 0)
            remaining  = sdata.get("remaining_count", 0)

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Assignments", total_asgn)
            m2.metric("Submitted ",       submitted)
            m3.metric("Remaining ",       remaining)

            # donut
            if total_asgn > 0:
                fig = go.Figure(go.Pie(
                    labels=["Submitted", "Remaining"],
                    values=[submitted, max(remaining,0)],
                    hole=0.6,
                    marker_colors=["#22c55e","#e2e8f0"],
                ))
                fig.update_layout(margin=dict(t=10,b=10), height=240)
                st.plotly_chart(fig, use_container_width=True)

            # assignments table
            st.markdown("### My Assignments")
            assignments_list = sdata.get("assignments", [])
            for a in assignments_list:
                status = a.get("status","Not Submitted")
                chip   = "chip-green" if status == "Accepted" else "chip-red"
                deadline = a.get("deadline","")[:10] if a.get("deadline") else "—"
                submitted_at = a.get("submittedAt","")[:19] if a.get("submittedAt") else "—"
                url = a.get("url","")
                st.markdown(
                    f"<div class='card'>"
                    f"<div class='title'>{a.get('title','Untitled')} "
                    f"<span class='chip {chip}'>{status}</span></div>"
                    f"<div class='meta'>"
                    f"Deadline: {deadline} | "
                    f"{'Submitted: ' + submitted_at if status=='Accepted' else 'Not submitted yet'}"
                    f"{'  |  <a href=\"' + url + '\" target=\"_blank\">View</a>' if url else ''}"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

        # ─────────────────────────────────────────
        # SUBMIT ASSIGNMENT
        # ─────────────────────────────────────────
        elif student_page == "📝 Submit Assignment":
            st.markdown("## Submit Assignment")
            st.markdown(f"Submitting as **{student.get('name','')}** (Roll #{roll_no})")

            # show available assignments
            assignments_list = sdata.get("assignments", [])
            pending = [a for a in assignments_list if a.get("status","") != "Accepted"]

            if pending:
                st.markdown(f"**{len(pending)} assignment(s) pending:**")
                options = {a["title"]: a["assignment_id"] for a in pending}
                sel_title = st.selectbox("Select Assignment", list(options.keys()))
                sel_aid   = options[sel_title]
            else:
                st.success("🎉 All assignments submitted!")
                sel_aid = ""
                sel_title = ""

            sub_url = st.text_input("Submission URL", placeholder="https://github.com/yourrepo")

            if st.button("Submit") and sel_aid and sub_url.strip():
                with st.spinner("Scraping & checking similarity…"):
                    result, re = post("/assignments/submit", {
                        "roll_no": roll_no,
                        "assignment_id": sel_aid,
                        "url": sub_url.strip()
                    })
                if re:
                    err(re)
                else:
                    st.success(result.get("message","Submitted!"))
                    # refresh student data
                    st.session_state.pop("student_data", None)
                    st.rerun()

            # manual assignment id entry
            st.markdown("---")
            st.markdown("##### Or enter Assignment ID manually")
            manual_aid = st.text_input("Assignment ObjectId (manual)")
            manual_url = st.text_input("URL (manual)", key="manual_url")
            if st.button("Submit (manual)") and manual_aid.strip() and manual_url.strip():
                with st.spinner("Submitting…"):
                    result, re = post("/assignments/submit", {
                        "roll_no": roll_no,
                        "assignment_id": manual_aid.strip(),
                        "url": manual_url.strip()
                    })
                if re: err(re)
                else:
                    st.success(result.get("message","Submitted!"))
                    st.session_state.pop("student_data", None)
                    st.rerun()

        # ─────────────────────────────────────────
        # MY NOTIFICATIONS
        # ─────────────────────────────────────────
        elif student_page == " My Notifications":
            st.markdown("## My Notifications")

            data, de = get(f"/notifications/student/{roll_no}")
            if de: err(de)
            else:
                st.metric("Notifications", data["count"])
                notifs = data.get("data", [])
                if not notifs:
                    st.info(" No notifications. You're all caught up!")
                else:
                    for n in notifs:
                        msg  = n.get("message","")
                        aid  = n.get("assignmentId","")
                        ts   = n.get("createdAt",{})
                        if isinstance(ts,dict): ts=ts.get("$date","")
                        st.markdown(
                            f"<div class='notif-box-student'>"
                            f"<div class='notif-title'>📋 Admin Notification</div>"
                            f"{msg}<br>"
                            f"<span style='font-size:0.7rem;color:#94a3b8;'>Assignment ID: {aid} | {str(ts)[:19]}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

    else:
        st.info(" Enter your roll number above and click **Load My Data** to get started.")