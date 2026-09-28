import boto3
from botocore.config import Config
from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}   # ← forces path-style: s3.region.amazonaws.com/bucket/key
    )                                      #   instead of virtual-hosted: bucket.s3.amazonaws.com/key
)

def upload_presigned_url(filename, expiration=1000):
    try:
        url = s3_client.generate_presigned_url( 
            "put_object",
            Params={
                "Bucket": settings.AWS_BUCKET_NAME, 
                "Key": filename,
                "ContentType": 'application/pdf'
                }, 
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f'Upload url generation issue: {e}')
        return None


def get_presigned_url(filename, expiration=3600):
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_BUCKET_NAME, 'Key': filename},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Link generation failed: {e}")
        return None
    
def get_presigned_preview_url(filename, expiration=300):
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_BUCKET_NAME,
                'Key': filename,
                'ResponseContentDisposition': 'inline',
                'ResponseContentType': 'application/pdf',
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Link generation failed: {e}")
        return None

def delete_from_s3(filename):
    try:
        s3_client.delete_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=filename
        )
        return True
    except Exception as e:
        print(f"Deletion failed: {e}")
        return False