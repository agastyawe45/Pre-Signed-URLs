import os
import boto3
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

# AWS Configurations
S3_BUCKET = os.getenv("S3_BUCKET", "default-s3-bucket")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")  # E.g., d123abc.cloudfront.net
REGION = os.getenv("AWS_REGION", "us-west-2")

# Initialize AWS Clients
s3 = boto3.client("s3", region_name=REGION)

# Logging setup
logging.basicConfig(level=logging.INFO)

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    try:
        data = request.json
        student_name = data.get("student_name")
        file_name = data.get("file_name")
        file_type = data.get("file_type")

        if not all([student_name, file_name, file_type]):
            return jsonify({"error": "Missing required parameters"}), 400

        # Construct S3 key based on student name and file name
        s3_key = f"{student_name}/{file_name}"

        # Generate pre-signed URL for CloudFront
        expires_at = datetime.utcnow() + timedelta(seconds=300)
        cloudfront_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"

        logging.info(f"Generated CloudFront URL: {cloudfront_url}")
        return jsonify({"url": cloudfront_url, "s3_key": s3_key})
    except Exception as e:
        logging.error(f"Error generating pre-signed URL: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
