import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, request, session, jsonify
from flask_cors import CORS
import boto3
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-me")
CORS(app)

PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

s3 = boto3.client(
    service_name="s3",
    endpoint_url=os.getenv("endpoint_url"),
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key"),
    region_name="auto",
)
BUCKET_NAME = os.getenv("BUCKET_NAME", "cdn")
CDN_DOMAIN = os.getenv("CDN_DOMAIN", "cdn.ayushanand.com")

client = MongoClient(os.getenv("MONGO_URI"))
db = client["cdn_db"]
files_collection = db["files"]


def cleanup_expired_files():
    now = datetime.utcnow()
    expired_files = files_collection.find({"expiration_date": {"$lt": now, "$ne": None}})
    for f in expired_files:
        try:
            s3.delete_object(Bucket=BUCKET_NAME, Key=f["r2_key"])
        except Exception as e:
            print(f"Failed to delete {f['r2_key']} from R2: {e}")
        files_collection.delete_one({"_id": f["_id"]})


@app.get("/")
def home():
    if session.get("authenticated"):
        return render_template("index.html")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect("/")
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == PASSWORD:
            session["authenticated"] = True
            return redirect("/")
        else:
            error = "Incorrect password. Please try again."
    return render_template("login.html", error=error)


@app.get("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect("/login")


@app.post("/upload")
def upload():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("file")
    expiry_days_str = request.form.get("expiry_days", "never")

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename
    r2_key = filename

    base, ext = os.path.splitext(filename)
    counter = 1
    existing_file = files_collection.find_one({"r2_key": r2_key})
    while existing_file:
        r2_key = f"{base}_{counter}{ext}"
        existing_file = files_collection.find_one({"r2_key": r2_key})
        counter += 1

    expiration_date = None
    if expiry_days_str and expiry_days_str != "never":
        try:
            days = int(expiry_days_str)
            expiration_date = datetime.utcnow() + timedelta(days=days)
        except ValueError:
            pass

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    try:
        s3.upload_fileobj(file, BUCKET_NAME, r2_key)
    except Exception as e:
        print(f"R2 Upload Error: {e}")
        return jsonify({"error": "Failed to upload to object storage"}), 500

    files_collection.insert_one({
        "name": filename,
        "r2_key": r2_key,
        "size": file_size,
        "upload_date": datetime.utcnow(),
        "expiration_date": expiration_date,
    })
    return jsonify({"success": True, "filename": filename, "r2_key": r2_key})


@app.get("/files")
def list_files():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401

    cleanup_expired_files()

    files = []
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        for obj in response.get("Contents", []):
            r2_key = obj["Key"]
            date_str = obj["LastModified"].isoformat()
            if not date_str.endswith("Z") and "+" not in date_str.split("T")[-1]:
                date_str += "Z"
            files.append({
                "name": r2_key,
                "size": obj["Size"],
                "date": date_str,
                "url": f"https://{CDN_DOMAIN}/{r2_key}",
            })
    except Exception as e:
        print(f"Error fetching from R2: {e}")
        return jsonify({"error": "Failed to fetch files from server"}), 500

    files.sort(key=lambda f: f["date"], reverse=True)
    return jsonify(files)


@app.delete("/file/<path:filename>")
def delete_file(filename):
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=filename)
        files_collection.delete_one({"r2_key": filename})
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")
        return jsonify({"error": "Failed to delete file"}), 500


if __name__ == "__main__":
    app.run(debug=True)