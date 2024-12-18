import os
import boto3
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

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
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    try:
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": file_name,
                "ContentType": file_type
            },
            ExpiresIn=300  # URL expires in 5 minutes
        )
        return jsonify({"url": presigned_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
