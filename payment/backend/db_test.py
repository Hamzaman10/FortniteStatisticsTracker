import boto3
from botocore.exceptions import ClientError

print("--- STARTING DB TEST ---")

# 1. Use standard credential chain (like the CLI uses)
try:
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    print("1. Boto3 Resource Created")
except Exception as e:
    print(f"FAILED to create resource: {e}")
    exit()

# 2. Try to list tables (Checks permissions)
try:
    print("2. Attempting to list tables...")
    tables = list(dynamodb.tables.all())
    print(f"   SUCCESS! Found tables: {[t.name for t in tables]}")
except Exception as e:
    print(f"FAILED to list tables. Credential/Permission error: {e}")

# 3. Try to access your specific table
try:
    print("3. Checking 'PaymentMethods' table...")
    table = dynamodb.Table("PaymentMethods")
    # specific check to see if table exists
    status = table.table_status
    print(f"   SUCCESS! Table status is: {status}")
except ClientError as e:
    print(f"FAILED to find table 'PaymentMethods': {e}")
except Exception as e:
    print(f"FAILED with unknown error: {e}")

print("--- END DB TEST ---")