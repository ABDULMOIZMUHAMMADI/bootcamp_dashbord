from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId, json_util
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

from scraper import get_content
from similarity import get_similarity

# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client["test"]

users_collection       = db["users"]
domains_collection     = db["domains"]
bootcamps_collection   = db["bootcamps"]
assignments_collection = db["assignments"]
student_assignments    = db["student_assignments"]
notifications_col      = db["notifications"]
attendance_collection  = db["attendance"]

app = FastAPI(title="Bootcamp Tracker API")


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def safe_oid(oid_str: str) -> ObjectId:
    try:
        return ObjectId(oid_str)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid ObjectId: {oid_str}")

def flex_id(value: str) -> dict:
    """
    Returns a $in query that matches the field whether it was stored
    as a plain string OR as an ObjectId. Solves the most common
    'students not found' bug caused by inconsistent ID types in MongoDB.
    Example: flex_id("abc123") → {"$in": ["abc123", ObjectId("abc123")]}
    """
    try:
        return {"$in": [value, ObjectId(value)]}
    except Exception:
        return value

def to_json(data):
    return json.loads(json_util.dumps(data))

def utcnow() -> datetime:
    """Always return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def get_all_domains() -> list[dict]:
    """Fetch all domains from DB (never hardcoded)."""
    return list(domains_collection.find())

def get_all_bootcamps() -> list[dict]:
    """Fetch all bootcamps from DB (never hardcoded)."""
    return list(bootcamps_collection.find())

def build_domain_maps() -> tuple[dict, dict]:
    """Returns (id→name, id→teacherId) for all domains."""
    domains = get_all_domains()
    id_to_name    = {str(d["_id"]): d.get("name", "") for d in domains}
    id_to_teacher = {str(d["_id"]): str(d.get("teacherId", "")) for d in domains}
    return id_to_name, id_to_teacher

def build_bootcamp_map() -> dict:
    """Returns id→name for all bootcamps."""
    bootcamps = get_all_bootcamps()
    return {str(b["_id"]): b.get("name", "") for b in bootcamps}

def student_by_roll(roll_no: int) -> dict:
    student = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with roll number {roll_no}")
    return student

def enrich_student(s: dict) -> dict:
    """Add human-readable bootcamp / domain / teacher names — always from DB."""
    domain_id_to_name, domain_id_to_teacher = build_domain_maps()
    bootcamp_id_to_name = build_bootcamp_map()

    domain_id   = str(s.get("domainId", ""))
    bootcamp_id = str(s.get("studentBootcampId", ""))

    s["domainName"]   = domain_id_to_name.get(domain_id, domain_id)
    s["bootcampName"] = bootcamp_id_to_name.get(bootcamp_id, bootcamp_id)
    teacher_id        = domain_id_to_teacher.get(domain_id, "")
    s["teacherId"]    = teacher_id

    teacher = users_collection.find_one({"_id": safe_oid(teacher_id)}) if teacher_id else None
    s["teacherName"] = teacher.get("name", teacher_id) if teacher else teacher_id
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
    s = student_by_roll(roll_no)
    return to_json(enrich_student(s))


@app.get("/student/id/{student_id}")
def get_student_by_id(student_id: str):
    s = users_collection.find_one({"_id": safe_oid(student_id), "role": "student"})
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return to_json(enrich_student(s))


@app.get("/students/bootcamp/{bootcamp_id}")
def students_by_bootcamp(bootcamp_id: str):
    students = list(users_collection.find({"studentBootcampId": flex_id(bootcamp_id), "role": "student"}))
    enriched = [enrich_student(s) for s in students]
    return {"count": len(enriched), "data": to_json(enriched)}


@app.get("/students/domain/{domain_id}")
def students_by_domain(domain_id: str):
    students = list(users_collection.find({"domainId": flex_id(domain_id), "role": "student"}))
    enriched = [enrich_student(s) for s in students]
    return {"count": len(enriched), "data": to_json(enriched)}


# ═══════════════════════════════════════════════
# 2. STATS
# ═══════════════════════════════════════════════

@app.get("/stats/bootcamp/{bootcamp_id}")
def bootcamp_stats(bootcamp_id: str):
    domain_id_to_name, _ = build_domain_maps()
    bootcamp_id_to_name  = build_bootcamp_map()

    pipeline = [
        {"$match": {"role": "student", "studentBootcampId": flex_id(bootcamp_id)}},
        {"$group": {"_id": "$domainId", "count": {"$sum": 1}}}
    ]
    domain_data = list(users_collection.aggregate(pipeline))
    total = sum(d["count"] for d in domain_data)
    for d in domain_data:
        d["domainName"] = domain_id_to_name.get(str(d["_id"]), str(d["_id"]))

    return {
        "bootcamp_id": bootcamp_id,
        "bootcamp_name": bootcamp_id_to_name.get(bootcamp_id, bootcamp_id),
        "total_students": total,
        "domains": to_json(domain_data)
    }


@app.get("/stats/domain/{domain_id}")
def domain_stats(domain_id: str):
    domain_id_to_name, _ = build_domain_maps()
    bootcamp_id_to_name  = build_bootcamp_map()

    pipeline = [
        {"$match": {"role": "student", "domainId": flex_id(domain_id)}},
        {"$group": {"_id": "$studentBootcampId", "count": {"$sum": 1}}}
    ]
    bc_data = list(users_collection.aggregate(pipeline))
    total = sum(b["count"] for b in bc_data)
    for b in bc_data:
        b["bootcampName"] = bootcamp_id_to_name.get(str(b["_id"]), str(b["_id"]))

    return {
        "domain_id": domain_id,
        "domain_name": domain_id_to_name.get(domain_id, domain_id),
        "total_students": total,
        "bootcamps": to_json(bc_data)
    }


# ═══════════════════════════════════════════════
# 3. ADMIN PANEL – full bootcamp overview
# ═══════════════════════════════════════════════

@app.get("/admin/bootcamp-overview")
def admin_bootcamp_overview():
    """
    Dynamic: fetches all bootcamps and domains from DB.
    Uses aggregation to minimise round-trips.
    """
    bootcamps = get_all_bootcamps()
    domains   = get_all_domains()

    result = []
    for bc in bootcamps:
        bc_id   = str(bc["_id"])
        bc_name = bc.get("name", bc_id)
        domains_detail = []

        for dom in domains:
            dom_id     = str(dom["_id"])
            dom_name   = dom.get("name", dom_id)
            teacher_id = str(dom.get("teacherId", ""))

            # student ids in this domain × bootcamp
            student_docs = list(users_collection.find(
                {"role": "student", "studentBootcampId": flex_id(bc_id), "domainId": flex_id(dom_id)},
                {"_id": 1}
            ))
            student_ids   = [s["_id"] for s in student_docs]
            student_count = len(student_ids)

            # active assignments for this domain
            assignment_docs = list(assignments_collection.find(
                {"domain": flex_id(dom_id), "status": "Active"},
                {"_id": 1}
            ))
            assignment_ids    = [a["_id"] for a in assignment_docs]
            total_assignments = len(assignment_ids)

            submitted = 0
            submitted_students = 0
            if student_ids and assignment_ids:
                submitted = student_assignments.count_documents({
                    "studentId":    {"$in": student_ids},
                    "assignmentId": {"$in": assignment_ids},
                    "status": "Accepted"
                })
                submitted_students = len(student_assignments.distinct("studentId", {
                    "studentId":    {"$in": student_ids},
                    "assignmentId": {"$in": assignment_ids},
                    "status": "Accepted"
                }))

            domains_detail.append({
                "domain_id":              dom_id,
                "domain_name":            dom_name,
                "teacher_id":             teacher_id,
                "student_count":          student_count,
                "total_assignments":      total_assignments,
                "submitted_count":        submitted,
                "submitted_students":     submitted_students,
                "not_submitted_students": student_count - submitted_students,
            })

        result.append({
            "bootcamp_id":    bc_id,
            "bootcamp_name":  bc_name,
            "domains":        domains_detail,
            "total_students": sum(d["student_count"] for d in domains_detail),
        })

    return {"bootcamps": result}


# ═══════════════════════════════════════════════
# 4. ASSIGNMENTS
# ═══════════════════════════════════════════════

@app.get("/assignments/domain/{domain_id}")
def assignments_by_domain(domain_id: str):
    assignments = list(assignments_collection.find({"domain": flex_id(domain_id), "status": "Active"}))
    return {"count": len(assignments), "data": to_json(assignments)}


@app.get("/assignments/all")
def all_assignments(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    """All assignments with pagination."""
    assignments = list(assignments_collection.find({"status": "Active"}).skip(skip).limit(limit))
    total = assignments_collection.count_documents({"status": "Active"})
    return {"total": total, "skip": skip, "limit": limit, "count": len(assignments), "data": to_json(assignments)}


@app.get("/assignments/detail/{assignment_id}")
def assignment_detail(assignment_id: str):
    a = assignments_collection.find_one({"_id": safe_oid(assignment_id)})
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return to_json(a)


@app.get("/assignments/by-name/{name}")
def assignment_by_name(name: str):
    assignments = list(assignments_collection.find({"title": {"$regex": name, "$options": "i"}}))
    if not assignments:
        raise HTTPException(status_code=404, detail="No assignments found with that name")
    return {"count": len(assignments), "data": to_json(assignments)}


# ═══════════════════════════════════════════════
# 5. SUBMISSION ENDPOINTS
# ═══════════════════════════════════════════════

class Submission(BaseModel):
    roll_no: int
    assignment_id: str
    url: str


@app.post("/assignments/submit")
def submit_assignment(data: Submission):
    student         = student_by_roll(data.roll_no)
    student_obj_id  = student["_id"]
    assignment_obj_id = safe_oid(data.assignment_id)

    assignment = assignments_collection.find_one({"_id": assignment_obj_id, "status": "Active"})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or inactive")

    content = get_content(data.url)
    if not content or len(content) < 50:
        raise HTTPException(status_code=400, detail="Content not readable from URL")

    # Similarity check against all previous submissions of this student
    all_subs = student_assignments.find({"studentId": student_obj_id})
    for sub in all_subs:
        old_content = sub.get("content", "")
        if not old_content:
            continue
        similarity = get_similarity(content, old_content)
        if similarity > 60:
            raise HTTPException(
                status_code=400,
                detail=f"Rejected ❌ Similarity {similarity:.2f}% > 60% with a previous submission"
            )

    now = utcnow()
    student_assignments.update_one(
        {"studentId": student_obj_id, "assignmentId": assignment_obj_id},
        {"$set": {
            "URL":         data.url,
            "content":     content,
            "submittedAt": now,
            "status":      "Accepted",
            "rollNo":      data.roll_no,
        }},
        upsert=True
    )
    return {"message": "Assignment submitted successfully ✅"}


@app.get("/assignments/submissions/all")
def all_submissions(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    """
    All submissions with student + assignment info via $lookup aggregation
    (avoids N+1 queries).
    """
    pipeline = [
        {"$skip": skip},
        {"$limit": limit},
        {"$lookup": {
            "from": "users",
            "localField": "studentId",
            "foreignField": "_id",
            "as": "studentDoc"
        }},
        {"$lookup": {
            "from": "assignments",
            "localField": "assignmentId",
            "foreignField": "_id",
            "as": "assignmentDoc"
        }},
        {"$addFields": {
            "studentRollNo":   {"$arrayElemAt": ["$studentDoc.rollNo", 0]},
            "studentName":     {"$arrayElemAt": ["$studentDoc.name", 0]},
            "domainId":        {"$arrayElemAt": ["$studentDoc.domainId", 0]},
            "bootcampId":      {"$arrayElemAt": ["$studentDoc.studentBootcampId", 0]},
            "assignmentTitle": {"$arrayElemAt": ["$assignmentDoc.title", 0]},
        }},
        {"$project": {"studentDoc": 0, "assignmentDoc": 0, "content": 0}}
    ]
    subs  = list(student_assignments.aggregate(pipeline))
    total = student_assignments.count_documents({})

    domain_id_to_name, _ = build_domain_maps()
    bootcamp_id_to_name  = build_bootcamp_map()

    for s in subs:
        s["domainName"]   = domain_id_to_name.get(str(s.get("domainId", "")), "")
        s["bootcampName"] = bootcamp_id_to_name.get(str(s.get("bootcampId", "")), "")

    return {"total": total, "skip": skip, "limit": limit, "count": len(subs), "data": to_json(subs)}


@app.get("/assignments/submissions/by-assignment/{assignment_id}")
def submissions_by_assignment(assignment_id: str):
    aid = safe_oid(assignment_id)
    pipeline = [
        {"$match": {"assignmentId": aid}},
        {"$lookup": {
            "from": "users",
            "localField": "studentId",
            "foreignField": "_id",
            "as": "studentDoc"
        }},
        {"$addFields": {
            "studentRollNo": {"$arrayElemAt": ["$studentDoc.rollNo", 0]},
            "studentName":   {"$arrayElemAt": ["$studentDoc.name", 0]},
        }},
        {"$project": {"studentDoc": 0, "content": 0}}
    ]
    subs = list(student_assignments.aggregate(pipeline))
    return {"count": len(subs), "data": to_json(subs)}


@app.get("/assignments/submission/{student_id}/{assignment_id}")
def get_submission(student_id: str, assignment_id: str):
    sub = student_assignments.find_one({
        "studentId":    safe_oid(student_id),
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
    s          = enrich_student(student_by_roll(roll_no))
    student_id = s["_id"]
    domain_id  = str(s.get("domainId", ""))

    assignments = list(assignments_collection.find({"domain": flex_id(domain_id), "status": "Active"}))

    # Fetch all submissions for this student in one query
    sub_map = {
        str(sub["assignmentId"]): sub
        for sub in student_assignments.find({"studentId": student_id, "status": "Accepted"})
    }

    assignments_list = []
    for a in assignments:
        aid_str = str(a["_id"])
        sub     = sub_map.get(aid_str)
        assignments_list.append({
            "assignment_id": aid_str,
            "title":         a.get("title", "Untitled"),
            "deadline":      str(a.get("deadline", "")),
            "status":        sub.get("status", "Not Submitted") if sub else "Not Submitted",
            "submittedAt":   str(sub.get("submittedAt", "")) if sub else "",
            "url":           sub.get("URL", "") if sub else "",
        })

    student_notifs = list(notifications_col.find(
        {"studentId": str(student_id)},
        sort=[("createdAt", -1)],
        limit=20
    ))

    return {
        "student":          to_json(s),
        "total_assignments": len(assignments),
        "submitted_count":  len(sub_map),
        "remaining_count":  len(assignments) - len(sub_map),
        "assignments":      to_json(assignments_list),
        "notifications":    to_json(student_notifs),
    }


# ═══════════════════════════════════════════════
# 7. NOTIFICATIONS
# ═══════════════════════════════════════════════

@app.get("/notifications/admin")
def admin_notifications():
    notifs = list(notifications_col.find(sort=[("createdAt", -1)], limit=50))

    # Collect all unique IDs to batch-fetch
    student_ids    = []
    assignment_ids = []
    for n in notifs:
        sid = n.get("studentId")
        aid = n.get("assignmentId")
        try:
            student_ids.append(ObjectId(sid))
        except Exception:
            pass
        try:
            assignment_ids.append(ObjectId(aid))
        except Exception:
            pass

    # Batch fetch students and assignments
    students_map    = {str(s["_id"]): s for s in users_collection.find({"_id": {"$in": student_ids}})}
    assignments_map = {str(a["_id"]): a for a in assignments_collection.find({"_id": {"$in": assignment_ids}})}

    domain_id_to_name, _ = build_domain_maps()

    for n in notifs:
        sid     = str(n.get("studentId", ""))
        aid     = str(n.get("assignmentId", ""))
        student = students_map.get(sid)
        assign  = assignments_map.get(aid)

        n["studentRollNo"]   = student.get("rollNo") if student else None
        n["studentName"]     = student.get("name") if student else None
        n["domainName"]      = domain_id_to_name.get(str(student.get("domainId", "")), "") if student else ""
        n["assignmentTitle"] = assign.get("title") if assign else None

    return {"count": len(notifs), "data": to_json(notifs)}


@app.get("/notifications/student/{roll_no}")
def student_notifications(roll_no: int):
    s   = student_by_roll(roll_no)
    sid = str(s["_id"])
    notifs = list(notifications_col.find({"studentId": sid}, sort=[("createdAt", -1)], limit=20))
    return {"count": len(notifs), "data": to_json(notifs)}


@app.delete("/notifications/{notif_id}")
def delete_notification(notif_id: str):
    res = notifications_col.delete_one({"_id": safe_oid(notif_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted successfully"}


@app.get("/check-missed-assignments")
def check_missed_assignments():
    """Scan all students, create notifications for missed deadlines."""
    now = utcnow()

    # Batch-fetch all active assignments with a deadline in the past
    past_assignments = list(assignments_collection.find({
        "status": "Active",
        "deadline": {"$lt": now}
    }))

    if not past_assignments:
        return {"total_notifications": 0, "data": []}

    assignment_ids = [a["_id"] for a in past_assignments]

    # Map assignment_id → assignment doc
    assign_map = {a["_id"]: a for a in past_assignments}

    students = list(users_collection.find({"role": "student"}))

    # Batch-fetch all existing submissions for these assignments
    existing_subs = set(
        (str(s["studentId"]), str(s["assignmentId"]))
        for s in student_assignments.find({"assignmentId": {"$in": assignment_ids}})
    )

    # Batch-fetch already-created notifications to avoid duplicates
    existing_notifs = set(
        (n["studentId"], n["assignmentId"])
        for n in notifications_col.find({"assignmentId": {"$in": [str(a) for a in assignment_ids]}})
    )

    notifications = []
    for student in students:
        student_id  = student["_id"]
        domain_id   = student.get("domainId", "")
        bootcamp_id = student.get("studentBootcampId", "")

        for assignment in past_assignments:
            # Only assignments in the student's domain (compare as strings to handle ObjectId/string mix)
            if str(assignment.get("domain")) != str(domain_id):
                continue

            key       = (str(student_id), str(assignment["_id"]))
            notif_key = (str(student_id), str(assignment["_id"]))

            if key not in existing_subs and notif_key not in existing_notifs:
                notifications.append({
                    "studentId":    str(student_id),
                    "assignmentId": str(assignment["_id"]),
                    "message":      f"{student.get('name', 'Student')} (Roll #{student.get('rollNo')}) has not submitted '{assignment.get('title', 'assignment')}'",
                    "rollNo":       student.get("rollNo"),
                    "domainId":     domain_id,
                    "bootcampId":   bootcamp_id,
                    "createdAt":    now,
                })

    if notifications:
        notifications_col.insert_many(notifications)

    return {"total_notifications": len(notifications), "data": to_json(notifications)}


# ═══════════════════════════════════════════════
# 8. TEACHER DETAILS
# ═══════════════════════════════════════════════

@app.get("/teachers")
def get_teachers():
    teachers = list(users_collection.find({"role": "teacher"}))
    return {"count": len(teachers), "data": to_json(teachers)}


@app.get("/teacher/{teacher_id}")
def get_teacher(teacher_id: str):
    teacher = users_collection.find_one({"_id": safe_oid(teacher_id)})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return to_json(teacher)


# ═══════════════════════════════════════════════
# 9. SEARCH
# ═══════════════════════════════════════════════

@app.get("/search/student")
def search_student(roll_no: int = None, student_id: str = None):
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
    if roll_no:
        s = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    elif student_id:
        s = users_collection.find_one({"_id": safe_oid(student_id), "role": "student"})
    else:
        raise HTTPException(status_code=400, detail="Provide roll_no or student_id")
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    domain_id   = str(s.get("domainId", ""))
    student_oid = s["_id"]

    domain_id_to_name, _ = build_domain_maps()
    bootcamp_id_to_name  = build_bootcamp_map()

    total = assignments_collection.count_documents({"domain": domain_id, "status": "Active"})

    # Use aggregation to get submission + assignment title in one shot
    pipeline = [
        {"$match": {"studentId": student_oid, "status": "Accepted"}},
        {"$lookup": {
            "from": "assignments",
            "localField": "assignmentId",
            "foreignField": "_id",
            "as": "assignmentDoc"
        }},
        {"$addFields": {"assignmentTitle": {"$arrayElemAt": ["$assignmentDoc.title", 0]}}},
        {"$project": {"assignmentDoc": 0, "content": 0}}
    ]
    subs = list(student_assignments.aggregate(pipeline))

    submitted_list = [
        {
            "assignment_id": str(sub["assignmentId"]),
            "title":         sub.get("assignmentTitle", ""),
            "submittedAt":   str(sub.get("submittedAt", "")),
            "url":           sub.get("URL", ""),
        }
        for sub in subs
    ]

    return {
        "student_name":    s.get("name"),
        "roll_no":         s.get("rollNo"),
        "domain":          domain_id_to_name.get(domain_id, domain_id),
        "bootcamp":        bootcamp_id_to_name.get(str(s.get("studentBootcampId", "")), ""),
        "total_assignments": total,
        "submitted_count": len(subs),
        "remaining_count": total - len(subs),
        "submitted":       to_json(submitted_list),
    }


# ═══════════════════════════════════════════════
# 10. ATTENDANCE
# ═══════════════════════════════════════════════

@app.get("/attendance/late-today")
def late_comers_today():
    now         = utcnow()
    today_start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
    today_end   = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Use aggregation to avoid N+1 queries
    pipeline = [
        {"$match": {"status": "late", "checkInTime": {"$gte": today_start, "$lte": today_end}}},
        {"$lookup": {
            "from": "users",
            "localField": "studentId",
            "foreignField": "_id",
            "as": "studentDoc"
        }},
        {"$addFields": {
            "studentName": {"$arrayElemAt": ["$studentDoc.name", 0]},
            "rollNo":      {"$arrayElemAt": ["$studentDoc.rollNo", 0]},
        }},
        {"$project": {"studentDoc": 0}}
    ]
    records = list(attendance_collection.aggregate(pipeline))

    result = [
        {
            "studentName": r.get("studentName"),
            "rollNo":      r.get("rollNo"),
            "checkInTime": str(r.get("checkInTime")),
        }
        for r in records
    ]

    return {"total_late_today": len(result), "late_students": result}


@app.get("/attendance/late-percentage")
def late_percentage():
    """
    Aggregate attendance stats per student without per-student DB queries.
    """
    pipeline = [
        {"$group": {
            "_id":     "$studentId",
            "total":   {"$sum": 1},
            "late":    {"$sum": {"$cond": [{"$eq": ["$status", "late"]},    1, 0]}},
            "present": {"$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}},
            "absent":  {"$sum": {"$cond": [{"$eq": ["$status", "absent"]},  1, 0]}},
        }},
        {"$match": {"total": {"$gt": 0}}},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "_id",
            "as": "studentDoc"
        }},
        {"$addFields": {
            "studentName":      {"$arrayElemAt": ["$studentDoc.name",   0]},
            "rollNo":           {"$arrayElemAt": ["$studentDoc.rollNo", 0]},
            "late_percentage":  {"$round": [{"$multiply": [{"$divide": ["$late", "$total"]}, 100]}, 2]},
            "on_time_percentage": {"$round": [{"$multiply": [{"$divide": ["$present", "$total"]}, 100]}, 2]},
        }},
        {"$project": {"studentDoc": 0}},
        {"$sort": {"late_percentage": -1}}
    ]

    result = list(attendance_collection.aggregate(pipeline))
    total_late_students = sum(1 for r in result if r.get("late", 0) > 0)

    return {
        "total_students_with_late": total_late_students,
        "students": to_json(result)
    }


@app.get("/attendance/student/{roll_no}")
def student_late_history(roll_no: int):
    student = users_collection.find_one({"rollNo": roll_no, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    sid     = student["_id"]
    records = list(attendance_collection.find({"studentId": sid}, sort=[("checkInTime", -1)]))

    if not records:
        return {
            "studentName": student.get("name"),
            "rollNo":      roll_no,
            "message":     "No attendance records found"
        }

    total   = len(records)
    late    = sum(1 for r in records if r["status"] == "late")
    present = sum(1 for r in records if r["status"] == "present")
    absent  = sum(1 for r in records if r["status"] == "absent")

    history = [
        {
            "date":         str(r.get("checkInTime")),
            "status":       r.get("status"),
            "checkInTime":  str(r.get("checkInTime")),
            "checkOutTime": str(r.get("checkOutTime")),
        }
        for r in records
    ]

    return {
        "studentName":       student.get("name"),
        "rollNo":            roll_no,
        "total_days":        total,
        "late_days":         late,
        "present_days":      present,
        "absent_days":       absent,
        "late_percentage":   round((late / total) * 100, 2),
        "on_time_percentage": round((present / total) * 100, 2),
        "history":           history,
    }