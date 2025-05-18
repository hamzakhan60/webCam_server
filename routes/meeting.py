# routes/meeting.py
from flask import Blueprint, request, jsonify
from datetime import datetime , timezone
import random, string


meeting_bp = Blueprint("meeting", __name__)
mongo = None # Placeholder for MongoDB instance, to be set in app.py


def set_mongo(m):
    global mongo
    mongo = m


def generate_meeting_key(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@meeting_bp.route('/api/meetings/create', methods=['POST'])
def create_meeting():
    print("Creating meeting")
    data = request.json
    title = data.get("title")
    host_id = data.get("hostId")

    if not title or not host_id:
        return jsonify({"error": "title and hostId are required"}), 400

    meeting_key = generate_meeting_key()

    meeting = {
        "title": title,
        "hostId": host_id,
        "meetingKey": meeting_key,
        "createdAt": datetime.now(),
        "attendees": [],
        "reports": []
    }

    result = mongo.db.meetings.insert_one(meeting)
    print("Meeting created:", result)
    meeting["_id"] = str(result.inserted_id)

    return jsonify({
        "message": "Meeting created successfully",
        "meeting": {
            "id": meeting["_id"],
            "title": title,
            "hostId": host_id,
            "meetingKey": meeting_key
        }
    }), 201
