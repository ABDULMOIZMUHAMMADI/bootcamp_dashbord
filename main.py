from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId, json_util
import json
from datetime import datetime, UTC

from scraper import get_content
from similarity import get_similarity

# ─────────────────────────────────────────────
# DB CONNECTION (inline so no import side effects)
# ─────────────────────────────────────────────
MONGO_URL = "mongodb+srv://user:uS3er2060@bootcamptracker.roknckd.mongodb.net/"
client = MongoClient(MONGO_URL)
db = client["test"]

users_collection        = db["users"]
domains_collection      = db["domains"]
assignments_collection  = db["assignments"]
student_assignments     = db["student_assignments"]
notifications_col       = db["notifications"]

# ─────────────────────────────────────────────
# STATIC CONFIG  (matches database.py)
# ─────────────────────────────────────────────
BOOTCAMPS = [
    {"id": "69c538969d2f7dcce6f2df20", "name": "Bootcamp 4.0"},
    {"id": "69c63a4736adc54470ff7703", "name": "Bootcamp 3.0"},
    {"id": "69c63a5336adc54470ff7704", "name": "Bootcamp 2.0"},
]

DOMAINS = [
    {"id": "69c538969d2f7dcce6f2df24", "name": "Web Development",  "teacherId": "69c63afa36adc54470ff7707"},
    {"id": "69c538969d2f7dcce6f2df26", "name": "AI Engineering",   "teacherId": "69c63b6f36adc54470ff7708"},
    {"id": "69c53f3b0b619312a3c67d7c", "name": "UI UX",            "teacherId": "69c63b9436adc54470ff7709"},
]

DOMAIN_ID_TO_NAME   = {d["id"]: d["name"]       for d in DOMAINS}
DOMAIN_ID_TO_TEACHER= {d["id"]: d["teacherId"]  for d in DOMAINS}
BOOTCAMP_ID_TO_NAME = {b["id"]: b["name"]        for b in BOOTCAMPS}

# ─────────────────────────────────────────────
app = FastAPI(title="Bootcamp Tracker API")

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def safe_oid(oid_str: str) -> ObjectId:
    try:
        return ObjectId(oid_str)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid ObjectId: {oid_str}")

def to_json(data):
    return json.loads(json_util.dumps(data))

def student_by_roll(roll_no: int):
    """Return student doc by rollNo."""
    student = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with roll number {roll_no}")
    return student

def enrich_student(s: dict) -> dict:
    """Add human-readable bootcamp / domain / teacher names to a student doc."""
    domain_id   = s.get("domainId", "")
    bootcamp_id = s.get("studentBootcampId", "")
    s["domainName"]   = DOMAIN_ID_TO_NAME.get(domain_id, domain_id)
    s["bootcampName"] = BOOTCAMP_ID_TO_NAME.get(bootcamp_id, bootcamp_id)
    s["teacherId"]    = DOMAIN_ID_TO_TEACHER.get(domain_id, "")
    # look up teacher name from DB
    teacher = users_collection.find_one({"_id": safe_oid(s["teacherId"])}) if s["teacherId"] else None
    s["teacherName"]  = teacher.get("name", s["teacherId"]) if teacher else s["teacherId"]
    return s


# ═══════════════════════════════════════════════
# 1. STUDENTS – basic CRUD
# ═══════════════════════════════════════════════

@app.get("/students/count")
def total_students():
    count = users_collection.count_documents({"role": "student"})
    return {"total_students": count}


@app.get("/student/roll/{roll_no}")
def get_student_by_roll(roll_no: int):
    """Get student details by roll number."""
    s = student_by_roll(roll_no)
    s = enrich_student(s)
    return to_json(s)


@app.get("/student/id/{student_id}")
def get_student_by_id(student_id: str):
    """Get student details by ObjectId string."""
    s = users_collection.find_one({"_id": safe_oid(student_id), "role": "student"})
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    s = enrich_student(s)
    return to_json(s)


@app.get("/students/bootcamp/{bootcamp_id}")
def students_by_bootcamp(bootcamp_id: str):
    students = list(users_collection.find({"studentBootcampId": bootcamp_id, "role": "student"}))
    return {"count": len(students), "data": to_json(students)}


@app.get("/students/domain/{domain_id}")
def students_by_domain(domain_id: str):
    students = list(users_collection.find({"domainId": domain_id, "role": "student"}))
    return {"count": len(students), "data": to_json(students)}


# ═══════════════════════════════════════════════
# 2. STATS
# ═══════════════════════════════════════════════

@app.get("/stats/bootcamp/{bootcamp_id}")
def bootcamp_stats(bootcamp_id: str):
    pipeline = [
        {"$match": {"role": "student", "studentBootcampId": bootcamp_id}},
        {"$group": {"_id": "$domainId", "count": {"$sum": 1}}}
    ]
    domain_data = list(users_collection.aggregate(pipeline))
    total = sum(d["count"] for d in domain_data)
    # add domain names
    for d in domain_data:
        d["domainName"] = DOMAIN_ID_TO_NAME.get(d["_id"], d["_id"])
    return {"bootcamp_id": bootcamp_id, "bootcamp_name": BOOTCAMP_ID_TO_NAME.get(bootcamp_id, bootcamp_id),
            "total_students": total, "domains": to_json(domain_data)}


@app.get("/stats/domain/{domain_id}")
def domain_stats(domain_id: str):
    pipeline = [
        {"$match": {"role": "student", "domainId": domain_id}},
        {"$group": {"_id": "$studentBootcampId", "count": {"$sum": 1}}}
    ]
    bc_data = list(users_collection.aggregate(pipeline))
    total = sum(b["count"] for b in bc_data)
    for b in bc_data:
        b["bootcampName"] = BOOTCAMP_ID_TO_NAME.get(b["_id"], b["_id"])
    return {"domain_id": domain_id, "domain_name": DOMAIN_ID_TO_NAME.get(domain_id, domain_id),
            "total_students": total, "bootcamps": to_json(bc_data)}


# ═══════════════════════════════════════════════
# 3. ADMIN PANEL – full bootcamp overview
# ═══════════════════════════════════════════════

@app.get("/admin/bootcamp-overview")
def admin_bootcamp_overview():
    """
    For every bootcamp → every domain:
      - student count
      - total assignments in that domain
      - submitted count (Accepted)
      - not-submitted count
    """
    result = []
    for bc in BOOTCAMPS:
        bc_id = bc["id"]
        domains_detail = []
        for dom in DOMAINS:
            dom_id = dom["id"]

            # student count in this domain × bootcamp combo
            student_count = users_collection.count_documents({
                "role": "student",
                "studentBootcampId": bc_id,
                "domainId": dom_id
            })

            # assignments for this domain (we store domainId as string in assignments)
            assignments = list(assignments_collection.find({
                "domain": dom_id,
                "status": "Active"
            }))
            assignment_ids = [a["_id"] for a in assignments]
            total_assignments = len(assignments)

            # submissions for students in this domain×bootcamp
            # get student ids first
            student_ids = [s["_id"] for s in users_collection.find(
                {"role": "student", "studentBootcampId": bc_id, "domainId": dom_id},
                {"_id": 1}
            )]

            submitted = student_assignments.count_documents({
                "studentId": {"$in": student_ids},
                "assignmentId": {"$in": assignment_ids},
                "status": "Accepted"
            }) if student_ids and assignment_ids else 0

            # unique students who submitted at least one
            submitted_students = len(student_assignments.distinct("studentId", {
                "studentId": {"$in": student_ids},
                "status": "Accepted"
            })) if student_ids else 0

            not_submitted_students = student_count - submitted_students

            domains_detail.append({
                "domain_id": dom_id,
                "domain_name": dom["name"],
                "teacher_id": dom["teacherId"],
                "student_count": student_count,
                "total_assignments": total_assignments,
                "submitted_count": submitted,
                "submitted_students": submitted_students,
                "not_submitted_students": not_submitted_students,
            })

        result.append({
            "bootcamp_id": bc_id,
            "bootcamp_name": bc["name"],
            "domains": domains_detail,
            "total_students": sum(d["student_count"] for d in domains_detail),
        })

    return {"bootcamps": result}


# ═══════════════════════════════════════════════
# 4. ASSIGNMENTS
# ═══════════════════════════════════════════════

@app.get("/assignments/domain/{domain_id}")
def assignments_by_domain(domain_id: str):
    """All active assignments for a domain."""
    assignments = list(assignments_collection.find({"domain": domain_id, "status": "Active"}))
    return {"count": len(assignments), "data": to_json(assignments)}


@app.get("/assignments/all")
def all_assignments():
    """All assignments."""
    assignments = list(assignments_collection.find({"status": "Active"}))
    return {"count": len(assignments), "data": to_json(assignments)}


@app.get("/assignments/detail/{assignment_id}")
def assignment_detail(assignment_id: str):
    """Full details of one assignment by ObjectId."""
    a = assignments_collection.find_one({"_id": safe_oid(assignment_id)})
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return to_json(a)


@app.get("/assignments/by-name/{name}")
def assignment_by_name(name: str):
    """Find assignments by name (case-insensitive)."""
    assignments = list(assignments_collection.find({"title": {"$regex": name, "$options": "i"}}))
    if not assignments:
        raise HTTPException(status_code=404, detail="No assignments found with that name")
    return {"count": len(assignments), "data": to_json(assignments)}


# ═══════════════════════════════════════════════
# 5. SUBMISSION ENDPOINTS
# ═══════════════════════════════════════════════

class Submission(BaseModel):
    roll_no: int          # student uses roll number
    assignment_id: str
    url: str


@app.post("/assignments/submit")
def submit_assignment(data: Submission):
    """Submit an assignment using roll number."""
    # 1. resolve student from roll number
    student = student_by_roll(data.roll_no)
    student_obj_id = student["_id"]

    assignment_obj_id = safe_oid(data.assignment_id)

    # 2. check assignment
    assignment = assignments_collection.find_one({"_id": assignment_obj_id, "status": "Active"})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or inactive")

    # 3. scrape content
    content = get_content(data.url)
    if not content or len(content) < 50:
        raise HTTPException(status_code=400, detail="Content not readable from URL")

    # 4. similarity check against ALL previous submissions of this student
    all_subs = student_assignments.find({"studentId": student_obj_id})
    for sub in all_subs:
        old_content = sub.get("content", "")
        similarity = get_similarity(content, old_content)
        if similarity > 60:
            raise HTTPException(
                status_code=400,
                detail=f"Rejected ❌ Similarity {similarity:.2f}% > 60% with a previous submission"
            )

    # 5. upsert
    student_assignments.update_one(
        {"studentId": student_obj_id, "assignmentId": assignment_obj_id},
        {"$set": {
            "URL": data.url,
            "content": content,
            "submittedAt": datetime.utcnow(),
            "status": "Accepted",
            "rollNo": data.roll_no,
        }},
        upsert=True
    )
    return {"message": "Assignment submitted successfully ✅"}


@app.get("/assignments/submissions/all")
def all_submissions():
    """All submissions across all students."""
    subs = list(student_assignments.find())
    # enrich with student roll and assignment name
    enriched = []
    for s in subs:
        sid = s.get("studentId")
        aid = s.get("assignmentId")
        student = users_collection.find_one({"_id": sid}, {"rollNo": 1, "name": 1, "domainId": 1, "studentBootcampId": 1}) if sid else None
        assignment = assignments_collection.find_one({"_id": aid}, {"title": 1}) if aid else None
        s["studentRollNo"]  = student.get("rollNo") if student else None
        s["studentName"]    = student.get("name") if student else None
        s["domainName"]     = DOMAIN_ID_TO_NAME.get(student.get("domainId", ""), "") if student else ""
        s["bootcampName"]   = BOOTCAMP_ID_TO_NAME.get(student.get("studentBootcampId", ""), "") if student else ""
        s["assignmentTitle"]= assignment.get("title") if assignment else None
        enriched.append(s)
    return {"count": len(enriched), "data": to_json(enriched)}


@app.get("/assignments/submissions/by-assignment/{assignment_id}")
def submissions_by_assignment(assignment_id: str):
    """All submissions for a specific assignment."""
    aid = safe_oid(assignment_id)
    subs = list(student_assignments.find({"assignmentId": aid}))
    for s in subs:
        sid = s.get("studentId")
        student = users_collection.find_one({"_id": sid}, {"rollNo": 1, "name": 1}) if sid else None
        s["studentRollNo"] = student.get("rollNo") if student else None
        s["studentName"]   = student.get("name") if student else None
    return {"count": len(subs), "data": to_json(subs)}


@app.get("/assignments/submission/{student_id}/{assignment_id}")
def get_submission(student_id: str, assignment_id: str):
    """Single submission by student ObjectId + assignment ObjectId."""
    sub = student_assignments.find_one({
        "studentId": safe_oid(student_id),
        "assignmentId": safe_oid(assignment_id)
    })
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found")
    return to_json(sub)


# ═══════════════════════════════════════════════
# 6. STUDENT PANEL
# ═══════════════════════════════════════════════

@app.get("/student/panel/{roll_no}")
def student_panel(roll_no: int):
    """
    Full student dashboard:
    - personal details (bootcamp, domain, teacher)
    - all assignments in their domain
    - which they submitted / remaining
    - their notifications
    """
    s = student_by_roll(roll_no)
    s = enrich_student(s)
    student_id = s["_id"]
    domain_id  = s.get("domainId", "")

    # assignments for this domain
    assignments = list(assignments_collection.find({"domain": domain_id, "status": "Active"}))
    total_assignments = len(assignments)

    # what student submitted
    submitted_ids = set(
        str(sub["assignmentId"])
        for sub in student_assignments.find({"studentId": student_id, "status": "Accepted"})
    )

    assignments_list = []
    for a in assignments:
        aid_str = str(a["_id"])
        sub = student_assignments.find_one({"studentId": student_id, "assignmentId": a["_id"]})
        assignments_list.append({
            "assignment_id": aid_str,
            "title": a.get("title", "Untitled"),
            "deadline": str(a.get("deadline", "")),
            "status": sub.get("status", "Not Submitted") if sub else "Not Submitted",
            "submittedAt": str(sub.get("submittedAt", "")) if sub else "",
            "url": sub.get("URL", "") if sub else "",
        })

    submitted_count  = len(submitted_ids)
    remaining_count  = total_assignments - submitted_count

    # student notifications
    student_notifs = list(notifications_col.find(
        {"studentId": str(student_id)},
        sort=[("createdAt", -1)],
        limit=20
    ))

    return {
        "student": to_json(s),
        "total_assignments": total_assignments,
        "submitted_count": submitted_count,
        "remaining_count": remaining_count,
        "assignments": to_json(assignments_list),
        "notifications": to_json(student_notifs),
    }


# ═══════════════════════════════════════════════
# 7. NOTIFICATIONS
# ═══════════════════════════════════════════════

@app.get("/notifications/admin")
def admin_notifications():
    """Latest 50 admin notifications (missed submissions)."""
    notifs = list(notifications_col.find(sort=[("createdAt", -1)], limit=50))
    # enrich with roll numbers
    for n in notifs:
        sid = n.get("studentId", "")
        try:
            student = users_collection.find_one({"_id": ObjectId(sid)}, {"rollNo": 1, "name": 1, "domainId": 1})
            n["studentRollNo"] = student.get("rollNo") if student else None
            n["studentName"]   = student.get("name") if student else None
            n["domainName"]    = DOMAIN_ID_TO_NAME.get(student.get("domainId", ""), "") if student else ""
        except Exception:
            n["studentRollNo"] = None
            n["studentName"]   = None
            n["domainName"]    = ""
        aid = n.get("assignmentId", "")
        try:
            a = assignments_collection.find_one({"_id": ObjectId(aid)}, {"title": 1})
            n["assignmentTitle"] = a.get("title") if a else None
        except Exception:
            n["assignmentTitle"] = None
    return {"count": len(notifs), "data": to_json(notifs)}


@app.get("/notifications/student/{roll_no}")
def student_notifications(roll_no: int):
    """Notifications for a specific student by roll number."""
    s = student_by_roll(roll_no)
    sid = str(s["_id"])
    notifs = list(notifications_col.find({"studentId": sid}, sort=[("createdAt", -1)], limit=20))
    return {"count": len(notifs), "data": to_json(notifs)}


@app.get("/check-missed-assignments")
def check_missed_assignments():
    """Scan all students, create notifications for missed deadlines."""
    now = datetime.utcnow()
    notifications = []
    students = list(users_collection.find({"role": "student"}))

    for student in students:
        student_id  = student["_id"]
        domain_id   = student.get("domainId", "")
        bootcamp_id = student.get("studentBootcampId", "")

        assignments = list(assignments_collection.find({
            "domain": domain_id,
            "status": "Active"
        }))

        for assignment in assignments:
            deadline = assignment.get("deadline")
            if not deadline:
                continue
            if now > deadline:
                submission = student_assignments.find_one({
                    "studentId": student_id,
                    "assignmentId": assignment["_id"]
                })
                if not submission:
                    # avoid duplicate notifications
                    already = notifications_col.find_one({
                        "studentId": str(student_id),
                        "assignmentId": str(assignment["_id"])
                    })
                    if not already:
                        notif = {
                            "studentId": str(student_id),
                            "assignmentId": str(assignment["_id"]),
                            "message": f"{student.get('name', 'Student')} (Roll #{student.get('rollNo')}) has not submitted '{assignment.get('title', 'assignment')}'",
                            "rollNo": student.get("rollNo"),
                            "domainId": domain_id,
                            "bootcampId": bootcamp_id,
                            "createdAt": now
                        }
                        notifications.append(notif)

    if notifications:
        notifications_col.insert_many(notifications)

    return {"total_notifications": len(notifications), "data": to_json(notifications)}


# ═══════════════════════════════════════════════
# 8. TEACHER DETAILS
# ═══════════════════════════════════════════════

@app.get("/teachers")
def get_teachers():
    """All teachers."""
    teachers = list(users_collection.find({"role": "teacher"}))
    return {"count": len(teachers), "data": to_json(teachers)}


@app.get("/teacher/{teacher_id}")
def get_teacher(teacher_id: str):
    teacher = users_collection.find_one({"_id": safe_oid(teacher_id)})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return to_json(teacher)


# ═══════════════════════════════════════════════
# 9. SEARCH – student by roll OR id
# ═══════════════════════════════════════════════

@app.get("/search/student")
def search_student(roll_no: int = None, student_id: str = None):
    """Search student by roll_no or student_id query param."""
    if roll_no:
        s = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    elif student_id:
        s = users_collection.find_one({"_id": safe_oid(student_id), "role": "student"})
    else:
        raise HTTPException(status_code=400, detail="Provide roll_no or student_id")
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return to_json(enrich_student(s))


@app.get("/search/student-submissions")
def search_student_submissions(roll_no: int = None, student_id: str = None):
    """
    How many assignments a specific student submitted vs remaining.
    Search by roll_no or student_id.
    """
    if roll_no:
        s = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    elif student_id:
        s = users_collection.find_one({"_id": safe_oid(student_id), "role": "student"})
    else:
        raise HTTPException(status_code=400, detail="Provide roll_no or student_id")
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    domain_id  = s.get("domainId", "")
    student_oid = s["_id"]

    # total assignments in domain
    total = assignments_collection.count_documents({"domain": domain_id, "status": "Active"})

    # submitted
    subs = list(student_assignments.find({"studentId": student_oid, "status": "Accepted"}))

    submitted_list = []
    for sub in subs:
        a = assignments_collection.find_one({"_id": sub["assignmentId"]}, {"title": 1})
        submitted_list.append({
            "assignment_id": str(sub["assignmentId"]),
            "title": a.get("title") if a else "",
            "submittedAt": str(sub.get("submittedAt", "")),
            "url": sub.get("URL", ""),
        })

    return {
        "student_name": s.get("name"),
        "roll_no": s.get("rollNo"),
        "domain": DOMAIN_ID_TO_NAME.get(domain_id, domain_id),
        "bootcamp": BOOTCAMP_ID_TO_NAME.get(s.get("studentBootcampId", ""), ""),
        "total_assignments": total,
        "submitted_count": len(subs),
        "remaining_count": total - len(subs),
        "submitted": to_json(submitted_list),
    }
attendance_collection = db["attendance"]

from datetime import datetime, UTC

@app.get("/attendance/late-today")
def late_comers_today():
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = datetime.now(UTC).replace(hour=23, minute=59, second=59)

    late_records = list(attendance_collection.find({
        "status": "late",
        "checkInTime": {"$gte": today_start, "$lte": today_end}
    }))

    result = []

    for record in late_records:
        student = users_collection.find_one(
            {"_id": record["studentId"]},
            {"name": 1, "rollNo": 1}
        )

        result.append({
            "studentName": student.get("name") if student else None,
            "rollNo": student.get("rollNo") if student else None,
            "checkInTime": str(record.get("checkInTime")),
        })

    return {
        "total_late_today": len(result),   # ✅ NEW
        "late_students": result
    }


@app.get("/attendance/late-percentage")
def late_percentage():
    students = list(users_collection.find({"role": "student"}))

    result = []

    for student in students:
        sid = student["_id"]

        records = list(attendance_collection.find({"studentId": sid}))
        total = len(records)

        if total == 0:
            continue

        late = sum(1 for r in records if r["status"] == "late")
        present = sum(1 for r in records if r["status"] == "present")
        absent = sum(1 for r in records if r["status"] == "absent")

        late_percent = (late / total) * 100
        ontime_percent = (present / total) * 100

        result.append({
            "studentName": student.get("name"),
            "rollNo": student.get("rollNo"),
            "total_days": total,
            "late_days": late,
            "present_days": present,
            "absent_days": absent,
            "late_percentage": round(late_percent, 2),
            "on_time_percentage": round(ontime_percent, 2)
        })

    # sort highest late first
    result = sorted(result, key=lambda x: x["late_percentage"], reverse=True)

    # ✅ NEW: total late students (>0 late)
    total_late_students = sum(1 for r in result if r["late_days"] > 0)

    return {
        "total_students_with_late": total_late_students,
        "students": result
    }
@app.get("/attendance/student/{roll_no}")
def student_late_history(roll_no: int):
    # find student
    student = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    sid = student["_id"]

    records = list(attendance_collection.find(
        {"studentId": sid},
        sort=[("checkInTime", -1)]
    ))

    if not records:
        return {
            "studentName": student.get("name"),
            "rollNo": roll_no,
            "message": "No attendance records found"
        }

    total = len(records)
    late = sum(1 for r in records if r["status"] == "late")
    present = sum(1 for r in records if r["status"] == "present")
    absent = sum(1 for r in records if r["status"] == "absent")

    # percentages
    late_percent = (late / total) * 100
    ontime_percent = (present / total) * 100

    history = []

    for r in records:
        history.append({
            "date": str(r.get("checkInTime")),
            "status": r.get("status"),
            "checkInTime": str(r.get("checkInTime")),
            "checkOutTime": str(r.get("checkOutTime")),
        })

    return {
        "studentName": student.get("name"),
        "rollNo": roll_no,
        "total_days": total,
        "late_days": late,
        "present_days": present,
        "absent_days": absent,
        "late_percentage": round(late_percent, 2),
        "on_time_percentage": round(ontime_percent, 2),
        "history": history
    }

