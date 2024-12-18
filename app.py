from flask import Flask, request, render_template, jsonify
import boto3

app = Flask(__name__)

# Configuration
S3_BUCKET = "dynamic-uploads-YOUR_BUCKET_NAME"  # Replace with your S3 bucket name
REGION = "us-west-2"

# AWS S3 Client
s3 = boto3.client("s3", region_name=REGION)

# Serve the Student Profiles Page
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint to Generate Pre-Signed URLs
@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    data = request.json
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    try:
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": file_name, "ContentType": file_type},
            ExpiresIn=300  # 5 minutes
        )
        return jsonify({"url": presigned_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

