import os
import boto3
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

S3_BUCKET = os.getenv("S3_BUCKET", "default-s3-bucket")
REGION = os.getenv("AWS_REGION", "us-west-2")
s3 = boto3.client("s3", region_name=REGION)

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    data = request.json
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    if not file_name or not file_type:
        return jsonify({"error": "File name or file type is missing!"}), 400

    try:
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": file_name,
                "ContentType": file_type
            },
            ExpiresIn=300
        )
        return jsonify({"url": presigned_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
