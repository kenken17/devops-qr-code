import json
from io import BytesIO

import boto3
import qrcode
from botocore.exceptions import ClientError

# Loading Environment variable (AWS Access Key and Secret Key)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# Allowing CORS for local testing
origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS S3 Configuration
secret_name = "devops-qr-code"
region_name = "ap-southeast-1"

# Create a Secrets Manager client
session = boto3.session.Session()
client = session.client(service_name="secretsmanager", region_name=region_name)

try:
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
except ClientError as e:
    # For a list of exceptions thrown, see
    # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    raise e

secret = json.loads(get_secret_value_response["SecretString"])

s3 = boto3.client(
    "s3",
    aws_access_key_id=secret["aws_access_key_id"],
    aws_secret_access_key=secret["aws_secret_access_key"],
)

bucket_name = "ken-devops-qr-code"  # Add your bucket name here


@app.post("/generate-qr/")
async def generate_qr(url: str):
    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save QR Code to BytesIO object
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Generate file name for S3
    file_name = f"qr_codes/{url.split('//')[-1]}.png"

    try:
        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=img_byte_arr,
            ContentType="image/png",
            ACL="public-read",
        )

        # Generate the S3 URL
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        return {"qr_code_url": s3_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
