from pymongo import MongoClient
from datetime import datetime, UTC
from bson import ObjectId
import random
from dotenv import load_dotenv
import os

load_dotenv()

# Get MongoDB URL from env
MONGO_URL = os.getenv("MONGO_URL")
# -------------------------------
# MongoDB Connection
# -------------------------------
client = MongoClient(MONGO_URL)

db = client["test"]

users_collection = db["users"]
domains_collection = db["domains"]
assignments_collection = db["assignments"]
student_assignments = db["student_assignments"]

# # -------------------------------
# # CONFIG
# # -------------------------------
# BOOTCAMPS = [
#     {"id": "69c538969d2f7dcce6f2df20", "name": "Bootcamp 4.0"},
#     {"id": "69c63a4736adc54470ff7703", "name": "Bootcamp 3.0"},
#     {"id": "69c63a5336adc54470ff7704", "name": "Bootcamp 2.0"},
# ]

# DOMAINS = [
#     {"id": "69c538969d2f7dcce6f2df24", "name": "Web Development", "teacherId": "69c63afa36adc54470ff7707"},
#     {"id": "69c538969d2f7dcce6f2df26", "name": "AI Engineering", "teacherId": "69c63b6f36adc54470ff7708"},
#     {"id": "69c53f3b0b619312a3c67d7c", "name": "UI UX", "teacherId": "69c63b9436adc54470ff7709"},
# ]

# STUDENTS_PER_DOMAIN = 100

# # -------------------------------
# # Dummy Data
# # -------------------------------
# avatars = [
#     "https://i.pravatar.cc/150?img=1",
#     "https://i.pravatar.cc/150?img=2",
#     "https://i.pravatar.cc/150?img=3"
# ]

# bios = [
#     "Learning web development",
#     "Bootcamp student",
#     "Future developer"
# ]

# locations = ["Karachi", "Lahore", "Islamabad"]

# # -------------------------------
# # INSERT DOMAINS (SAFE)
# # -------------------------------
# for bootcamp in BOOTCAMPS:
#     for domain in DOMAINS:
#         domain_doc = {
#             "name": f"{domain['name']} ({bootcamp['name']})",
#             "description": f"{domain['name']} track in {bootcamp['name']}",
#             "bootcamp": ObjectId(bootcamp["id"]),
#             "status": "Active",
#             "type": "Core Track",
#             "mentorName": domain["teacherId"],
#             "studentsCount": 0,
#             "createdAt": datetime.utcnow(),
#             "updatedAt": datetime.utcnow(),
#             "__v": 0
#         }

#         existing = domains_collection.find_one({"name": domain_doc["name"]})
#         if existing:
#             print(f"Domain '{domain_doc['name']}' already exists ⚠️")
#         else:
#             domains_collection.insert_one(domain_doc)
#             print(f"Domain '{domain_doc['name']}' inserted ✅")

# # -------------------------------
# # INSERT STUDENTS
# # -------------------------------
# roll_no = 3000
# users = []

# for bootcamp in BOOTCAMPS:
#     for domain in DOMAINS:
#         for i in range(STUDENTS_PER_DOMAIN):
#             user = {
#                 "name": f"Student {roll_no}",
#                 "email": f"student{roll_no}@test.com",  # unique email
#                 "password": "$2b$10$dummyhashedpassword",
#                 "role": "student",
#                 "expoPushToken": None,
#                 "teacherBootcampIds": [],
#                 "studentBootcampId": bootcamp["id"],
#                 "domainId": domain["id"],
#                 "teacherDomainIds": [domain["teacherId"]],
#                 "studentStatus": "enrolled",
#                 "otp": None,
#                 "rollNo": roll_no,
#                 "isFirstLogin": False,
#                 "phone": f"03{random.randint(100000000, 999999999)}",
#                 "bio": random.choice(bios),
#                 "location": random.choice(locations),
#                 "avatar": random.choice(avatars),
#                 "lastNotificationCheck": datetime.now(UTC),
#                 "createdAt": datetime.now(UTC),
#                 "updatedAt": datetime.now(UTC),
#                 "__v": 0
#             }

#             users.append(user)
#             roll_no += 1

# # INSERT STUDENTS
# try:
#     users_collection.insert_many(users, ordered=False)
#     print(f"{len(users)} students inserted ✅")
# except Exception:
#     print("Some duplicate students skipped ⚠️")



# # Step 1: recent 1000 students lao (latest first)
# students = users_collection.find().sort("_id", -1).limit(1000)

# # Step 2: unke IDs nikalo
# ids = [student["_id"] for student in students]

# # Step 3: delete karo
# result = users_collection.delete_many({"_id": {"$in": ids}})

# print(f"Deleted {result.deleted_count} students")


