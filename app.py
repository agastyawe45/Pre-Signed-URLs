import os
import boto3
import logging
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS to handle requests from CloudFront
CORS(app, supports_credentials=True, origins="*")

# AWS Configurations
S3_BUCKET = os.getenv("S3_BUCKET", "default-s3-bucket")  # Bucket name passed via environment variable
REGION = os.getenv("AWS_REGION", "us-west-2")

# Initialize AWS S3 Client
s3 = boto3.client("s3", region_name=REGION)

# Serve the root path
@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

# Endpoint to generate pre-signed URLs
@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    data = request.json

    # Validate input
    student_name = data.get("student_name")
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    if not student_name or not file_name or not file_type:
        logger.error("Missing required fields in the request.")
        return jsonify({"error": "Missing required fields: student_name, file_name, or file_type"}), 400

    # Construct the S3 key with the student's name
    s3_key = f"{student_name}/{file_name}"

    try:
        # Generate the pre-signed URL
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": s3_key,
                "ContentType": file_type
            },
            ExpiresIn=300  # URL expires in 5 minutes
        )
        logger.info(f"Generated pre-signed URL for {s3_key}")
        return jsonify({"url": presigned_url, "s3_key": s3_key})
    except Exception as e:
        logger.error(f"Error generating pre-signed URL: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
