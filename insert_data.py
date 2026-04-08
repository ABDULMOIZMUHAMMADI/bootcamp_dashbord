# from pymongo import MongoClient
# from datetime import datetime, timedelta, UTC
# import random

# # -------------------------------
# # MongoDB Connection
# # -------------------------------
# MONGO_URL = "mongodb+srv://user:uS3er2060@bootcamptracker.roknckd.mongodb.net/"
# client = MongoClient(MONGO_URL)

# db = client["test"]

# users_collection = db["users"]
# attendance_collection = db["attendance"]

# # -------------------------------
# # CONFIG
# # -------------------------------
# DAYS = 7   # kitne din ka data generate karna hai

# # -------------------------------
# # FETCH STUDENTS ONLY
# # -------------------------------
# students = list(users_collection.find({"role": "student"}))

# attendance_records = []

# # -------------------------------
# # GENERATE DUMMY ATTENDANCE
# # -------------------------------
# for student in students:
#     student_id = student["_id"]
#     bootcamp_id = student.get("studentBootcampId")

#     for i in range(DAYS):
#         date = datetime.now(UTC) - timedelta(days=i)

#         # Random status
#         status = random.choice(["present", "absent", "late"])

#         # Base check-in time (9 AM)
#         check_in_time = date.replace(hour=9, minute=0, second=0, microsecond=0)

#         # Late case
#         if status == "late":
#             check_in_time += timedelta(minutes=random.randint(10, 60))

#         # Check-out (5 PM)
#         check_out_time = check_in_time + timedelta(hours=8)

#         # Absent case (no check-in/out)
#         if status == "absent":
#             check_in_time = None
#             check_out_time = None

#         record = {
#             "studentId": student_id,
#             "bootcampId": bootcamp_id,
#             "checkInTime": check_in_time,
#             "checkOutTime": check_out_time,
#             "status": status,
#             "createdAt": datetime.now(UTC),
#             "updatedAt": datetime.now(UTC),
#             "__v": 0
#         }

#         attendance_records.append(record)

# # -------------------------------
# # INSERT INTO DB
# # -------------------------------
# if attendance_records:
#     attendance_collection.insert_many(attendance_records)
#     print(f"{len(attendance_records)} attendance records inserted ✅")
# else:
#     print("No data inserted ❌")