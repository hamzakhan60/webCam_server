from flask import Flask, request, jsonify
import numpy as np
from datetime import datetime
import base64
import cv2
from analyzer import analyze_frame
from flask_pymongo import PyMongo
from config import MONGO_URI
from flask_bcrypt import Bcrypt
from flask_cors import CORS

app = Flask(__name__)
app.config["MONGO_URI"] = MONGO_URI
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app)



from routes.auth import auth_bp,set_auth_dependencies
set_auth_dependencies(mongo, bcrypt)  # Set dependencies for auth routes
app.register_blueprint(auth_bp)



from routes.meeting import meeting_bp,set_mongo
set_mongo(mongo) 
app.register_blueprint(meeting_bp)




@app.route('/api/meetings/join', methods=['POST'])
def join_meeting():
    data = request.json
    meeting_key = data.get("meetingKey")
    attendee = data.get("attendee")

    if not meeting_key or not attendee:
        return jsonify({"error": "Missing meetingKey or attendee"}), 400

    # Check if meeting exists
    meeting = mongo.db.meetings.find_one({"meetingKey": meeting_key})

    if not meeting:
        return jsonify({"error": "Meeting not found"}), 404
    
    
    # Check if attendee already exists
    existing_attendee = mongo.db.meetings.find_one({
        "_id": meeting["_id"],
        "attendees.email": attendee["email"]
    })


    if not existing_attendee:
    # Only push if not already present
        mongo.db.meetings.update_one(
            {"_id": meeting["_id"]},
            {"$push": {"attendees": attendee}}
        )

    return jsonify({"message": "Joined successfully"}), 200

@app.route('/api/meeting/<meeting_key>/report', methods=['GET'])
def get_attendees_focus(meeting_key):   
    print("Getting attendees focus for meeting:", meeting_key)
    # Find the meeting by meetingKey
    meeting = mongo.db.meetings.find_one({"meetingKey": meeting_key})
    if not meeting:
        return jsonify({"error": "Meeting not found"}), 404
    created_at = meeting.get("createdAt")
    if isinstance(created_at, str):
        # Parse string to datetime
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", ""))
        except Exception:
            return jsonify({"error": "Invalid date format in 'createdAt'"}), 400

    now = datetime.now()
    duration = (now - created_at).total_seconds()

    attendees = meeting.get("attendees", [])
    result = []

    for attendee in attendees:
        reports = attendee.get("reports", [])
        total_reports = len(reports)
        if total_reports == 0:
            focus_percentage = 0
        else:
            focused_count = sum(1 for r in reports if r.get("status") == "FOCUSED")
            focus_percentage = (focused_count / total_reports) * 100

        result.append({
            "name": attendee.get("name"),
            "email": attendee.get("email"),
            "status": reports[-1].get("status") if reports else None,
            "focusPercentage": round(focus_percentage, 2),
            "reportsCount": total_reports,
            "timePresent": reports[-1].get("time") if reports else None,
        })

    return jsonify({
        "meetingKey": meeting_key,
        "title": meeting.get("title"),
        "startTime": meeting.get("createdAt").isoformat(),
        "duration": duration,
        "attendees": result
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    meeting_key = data.get("meetingKey")
    attendee_email = data.get("attendeeEmail")
    attendee_image = data.get("screenshot")
    screenshot = data.get("screenshot")
      # base64 image from frontend
    
    if not meeting_key or not attendee_email or not attendee_image:
        return jsonify({"error": "meetingKey, attendeeEmail and screenshot are required"}), 400
    
    try:
        # Remove base64 prefix if present
        if attendee_image.startswith("data:image"):
            attendee_image = attendee_image.split(",")[1]

        # Decode base64 image to bytes
        image_bytes = base64.b64decode(attendee_image)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        cv2.imshow("Decoded Image", frame)  
        if frame is None:
            return jsonify({"error": "Invalid image data"}), 400
        print("Image decoded successfully")
        # Analyze frame (your own logic)
        status = analyze_frame(frame)
        print("Analysis result:", status)
        # Create report object
        report = {
            "time": datetime.utcnow().isoformat(),
            "status": status,
            "screenshot": screenshot  # Save raw base64 image string
        }

        # Push report to attendee's reports array
        result = mongo.db.meetings.update_one(
            {
                "meetingKey": meeting_key,
                "attendees.email": attendee_email
            },
            {
                "$push": {
                    "attendees.$.reports": report
                }
            }
        )

        if result.modified_count == 0:
            return jsonify({"error": "Meeting or attendee not found"}), 404

        return jsonify({"message": "Report added", "status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/report-history", methods=["GET"])
def get_report_history():
    meeting_key = request.args.get("meetingKey")
    attendee_email = request.args.get("email")

    if not meeting_key or not attendee_email:
        return jsonify({"error": "Missing meetingKey or email"}), 400

    meeting = mongo.db.meetings.find_one({"meetingKey": meeting_key})
    if not meeting:
        return jsonify({"error": "Meeting not found"}), 404

    # Find the attendee in the meeting
    attendee = next(
        (a for a in meeting.get("attendees", []) if a["email"] == attendee_email),
        None
    )

    if not attendee or "reports" not in attendee:
        return jsonify({"error": "Attendee or reports not found"}), 404

    # Map reports to desired format
    report_history = []

    reports = attendee.get("reports", [])
    total_reports = len(reports)
    if total_reports == 0:
        focus_percentage = 0
    else:
        focused_count = sum(1 for r in reports if r.get("status") == "FOCUSED")
        focus_percentage = (focused_count / total_reports) * 100
    report_history={
            "status": reports[-1].get("status") if reports else None,
            "focusScore": round(focus_percentage, 2),
            "timestamp": reports[-1].get("time") if reports else None,
            "screenshot": reports[-1].get("screenshot") if reports else None,
        }
   
       
    return jsonify(report_history), 200

if __name__ == "__main__":
    app.run(debug=True)
