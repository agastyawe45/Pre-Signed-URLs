import os
import rsa
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from botocore.signers import CloudFrontSigner

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

# CloudFront and AWS Configuration
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "./private_key.pem")
KEY_PAIR_ID = os.getenv("CLOUDFRONT_KEY_ID", "<your-key-pair-id>")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "<your-cloudfront-domain>")
S3_BUCKET = os.getenv("S3_BUCKET", "default-s3-bucket")

# Function to fetch the private key
def fetch_private_key():
    try:
        with open(PRIVATE_KEY_PATH, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        raise Exception(f"Private key file not found at {PRIVATE_KEY_PATH}")

# Function to sign messages with the private key
def rsa_signer(message):
    private_key = fetch_private_key()
    key = rsa.PrivateKey.load_pkcs1(private_key)
    return rsa.sign(message, key, "SHA-1")

# Generate CloudFront signed URL
@app.route("/generate-url", methods=["POST"])
def generate_signed_url():
    data = request.json
    student_name = data.get("student_name")
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    # Construct the S3 key and CloudFront URL
    s3_key = f"{student_name}/{file_name}"
    cloudfront_url = f"{CLOUDFRONT_DOMAIN}/{s3_key}"

    signer = CloudFrontSigner(KEY_PAIR_ID, rsa_signer)
    expiration_time = datetime.utcnow() + timedelta(seconds=3600)

    try:
        signed_url = signer.generate_presigned_url(
            cloudfront_url, date_less_than=expiration_time
        )
        return jsonify({"url": signed_url, "s3_key": s3_key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
