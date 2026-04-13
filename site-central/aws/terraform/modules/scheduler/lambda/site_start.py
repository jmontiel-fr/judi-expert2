"""
Lambda function to start the Judi-Expert Site Central.

Triggered by EventBridge Scheduler at 8h (Europe/Paris) on weekdays.
1. Starts the RDS PostgreSQL instance and waits for availability.
2. Scales the ECS Fargate service to desired count (1).
"""

import os
import time

import boto3

ECS_CLUSTER = os.environ["ECS_CLUSTER"]
ECS_SERVICE = os.environ["ECS_SERVICE"]
RDS_INSTANCE_ID = os.environ["RDS_INSTANCE_ID"]

ecs = boto3.client("ecs")
rds = boto3.client("rds")


def handler(event, context):
    print(f"Starting site: RDS={RDS_INSTANCE_ID}, ECS={ECS_CLUSTER}/{ECS_SERVICE}")

    # --- Start RDS instance ---
    try:
        rds.start_db_instance(DBInstanceIdentifier=RDS_INSTANCE_ID)
        print(f"RDS start_db_instance called for {RDS_INSTANCE_ID}")
    except rds.exceptions.InvalidDBInstanceStateFault:
        print("RDS instance is already starting or available")

    # Wait for RDS to become available (poll every 15s, max ~4min)
    for attempt in range(16):
        response = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
        status = response["DBInstances"][0]["DBInstanceStatus"]
        print(f"RDS status (attempt {attempt + 1}): {status}")
        if status == "available":
            break
        time.sleep(15)
    else:
        print("WARNING: RDS did not become available within timeout, proceeding with ECS start")

    # --- Scale ECS service to nominal ---
    ecs.update_service(
        cluster=ECS_CLUSTER,
        service=ECS_SERVICE,
        desiredCount=1,
    )
    print(f"ECS service {ECS_SERVICE} scaled to desiredCount=1")

    return {"statusCode": 200, "body": "Site started successfully"}
