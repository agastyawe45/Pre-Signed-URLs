import os
import rsa
from datetime import datetime, timedelta
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from botocore.signers import CloudFrontSigner
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

# AWS Configurations
S3_BUCKET = os.getenv("BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "us-west-2")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")
CLOUDFRONT_KEY_PAIR_ID = os.getenv("CLOUDFRONT_KEY_PAIR_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "/home/ubuntu/cloudfront_private_key.pem")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to fetch the private key
def fetch_private_key() -> bytes:
    try:
        with open(PRIVATE_KEY_PATH, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        logger.error(f"Private key file not found at {PRIVATE_KEY_PATH}")
        raise

# Function to sign the policy with RSA private key
def rsa_signer(message: bytes) -> bytes:
    try:
        private_key = fetch_private_key()
        key = rsa.PrivateKey.load_pkcs1(private_key)
        return rsa.sign(message, key, "SHA-1")
    except Exception as e:
        logger.error(f"Error signing message: {str(e)}")
        raise

# Function to generate CloudFront signed URLs
def generate_signed_url(resource_path: str, expires_in: int = 3600) -> str:
    cf_signer = CloudFrontSigner(CLOUDFRONT_KEY_PAIR_ID, rsa_signer)

    # Define expiration time
    expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)

    # Generate signed URL
    try:
        signed_url = cf_signer.generate_presigned_url(
            f"{CLOUDFRONT_DOMAIN}/{resource_path}", date_less_than=expiration_time
        )
        return signed_url
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise

# Route to serve the main page
@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

# API to generate CloudFront pre-signed URL for uploading to S3
@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    data = request.json
    student_name = data.get("student_name")
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    if not student_name or not file_name or not file_type:
        return jsonify({"error": "Missing required fields"}), 400

    # Construct the S3 key using the student name and file name
    s3_key = f"{student_name}/{file_name}"

    try:
        # Generate CloudFront signed URL
        signed_url = generate_signed_url(s3_key)
        return jsonify({"url": signed_url, "s3_key": s3_key})
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
