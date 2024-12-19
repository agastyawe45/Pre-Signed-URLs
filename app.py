import boto3
import os
import rsa
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from botocore.signers import CloudFrontSigner

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to fetch AWS configurations from SSM Parameter Store
def fetch_cloudfront_config():
    try:
        ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "us-west-2"))
        cloudfront_domain = ssm.get_parameter(Name="/flask-app/cloudfront_domain")["Parameter"]["Value"]
        cloudfront_key_id = ssm.get_parameter(Name="/flask-app/cloudfront_key_pair_id")["Parameter"]["Value"]
        return cloudfront_domain, cloudfront_key_id
    except Exception as e:
        logger.error(f"Error fetching CloudFront configuration from SSM: {e}")
        raise

# Fetch configurations and set them in the app
try:
    cloudfront_domain, cloudfront_key_id = fetch_cloudfront_config()
    app.config["CLOUDFRONT_DOMAIN"] = cloudfront_domain
    app.config["CLOUDFRONT_KEY_PAIR_ID"] = cloudfront_key_id
    app.config["PRIVATE_KEY_PATH"] = os.getenv("PRIVATE_KEY_PATH", "/home/ubuntu/cloudfront_private_key.pem")
except Exception as e:
    logger.error("Failed to initialize CloudFront configuration.")
    raise

# Function to fetch the private key
def fetch_private_key() -> bytes:
    try:
        with open(app.config["PRIVATE_KEY_PATH"], "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        logger.error(f"Private key file not found at {app.config['PRIVATE_KEY_PATH']}")
        raise FileNotFoundError(f"Private key file not found at {app.config['PRIVATE_KEY_PATH']}")

# Function to sign the policy with RSA private key
def rsa_signer(message: bytes) -> bytes:
    try:
        private_key = fetch_private_key()
        key = rsa.PrivateKey.load_pkcs1(private_key)
        return rsa.sign(message, key, "SHA-1")
    except Exception as e:
        logger.error(f"Error signing message: {str(e)}")
        raise RuntimeError(f"Error signing message: {str(e)}")

# Function to generate CloudFront signed URLs
def generate_signed_url(resource_path: str, expires_in: int = 3600) -> str:
    cf_signer = CloudFrontSigner(app.config["CLOUDFRONT_KEY_PAIR_ID"], rsa_signer)

    # Define expiration time
    expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)

    # Generate signed URL
    try:
        signed_url = cf_signer.generate_presigned_url(
            f"{app.config['CLOUDFRONT_DOMAIN']}/{resource_path}",
            date_less_than=expiration_time
        )
        logger.info(f"Generated signed URL: {signed_url}")
        return signed_url
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise RuntimeError(f"Error generating signed URL: {e}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate-url", methods=["POST"])
def generate_presigned_url():
    data = request.json
    student_name = data.get("student_name")
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    if not student_name or not file_name or not file_type:
        logger.error("Missing required fields in the request")
        return jsonify({"error": "Missing required fields"}), 400

    # Construct the S3 key using the student name and file name
    s3_key = f"{student_name}/{file_name}"

    try:
        # Generate CloudFront signed URL
        signed_url = generate_signed_url(s3_key)
        logger.info(f"Successfully generated URL for {s3_key}")
        return jsonify({"url": signed_url, "s3_key": s3_key})
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
