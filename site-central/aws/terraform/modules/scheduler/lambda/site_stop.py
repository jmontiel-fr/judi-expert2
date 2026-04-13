"""
Lambda function to stop the Judi-Expert Site Central.

Triggered by EventBridge Scheduler at 20h (Europe/Paris) on weekdays.
1. Scales the ECS Fargate service to 0 (no running tasks).
2. Stops the RDS PostgreSQL instance.
"""

import os

import boto3

ECS_CLUSTER = os.environ["ECS_CLUSTER"]
ECS_SERVICE = os.environ["ECS_SERVICE"]
RDS_INSTANCE_ID = os.environ["RDS_INSTANCE_ID"]

ecs = boto3.client("ecs")
rds = boto3.client("rds")


def handler(event, context):
    print(f"Stopping site: RDS={RDS_INSTANCE_ID}, ECS={ECS_CLUSTER}/{ECS_SERVICE}")

    # --- Scale ECS to zero ---
    ecs.update_service(
        cluster=ECS_CLUSTER,
        service=ECS_SERVICE,
        desiredCount=0,
    )
    print(f"ECS service {ECS_SERVICE} scaled to desiredCount=0")

    # --- Stop RDS instance ---
    try:
        rds.stop_db_instance(DBInstanceIdentifier=RDS_INSTANCE_ID)
        print(f"RDS stop_db_instance called for {RDS_INSTANCE_ID}")
    except rds.exceptions.InvalidDBInstanceStateFault:
        print("RDS instance is already stopping or stopped")

    return {"statusCode": 200, "body": "Site stopped successfully"}
