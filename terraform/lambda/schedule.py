"""Reconcile operating hours without waiting inside Lambda for RDS startup."""
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def should_run(now):
    if now.year != int(os.environ["HOLIDAY_CALENDAR_YEAR"]):
        return False
    return (now.weekday() < 5 and 10 <= now.hour < 22
            and now.date().isoformat() not in json.loads(os.environ["HOLIDAY_DATES"]))


def reconcile(now, ec2, rds, dns):
    instance_id = os.environ["INSTANCE_ID"]
    db_id = os.environ["DB_ID"]
    instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
    ec2_state = instance["State"]["Name"]
    db_state = rds.describe_db_instances(DBInstanceIdentifier=db_id)["DBInstances"][0]["DBInstanceStatus"]
    running = should_run(now)
    logger.info("desired_running=%s ec2=%s rds=%s", running, ec2_state, db_state)
    if running:
        if db_state == "stopped":
            rds.start_db_instance(DBInstanceIdentifier=db_id)
        elif db_state == "available":
            if ec2_state == "stopped":
                ec2.start_instances(InstanceIds=[instance_id])
            elif ec2_state == "running":
                ip = instance.get("PublicIpAddress")
                if not ip:
                    raise RuntimeError("Running EC2 has no public IPv4 address")
                name = os.environ["ORIGIN_DOMAIN"].rstrip(".") + "."
                records = dns.list_resource_record_sets(
                    HostedZoneId=os.environ["ZONE_ID"], StartRecordName=name,
                    StartRecordType="A", MaxItems="1")["ResourceRecordSets"]
                if not records or records[0]["Name"] != name or records[0].get("ResourceRecords") != [{"Value": ip}]:
                    dns.change_resource_record_sets(
                        HostedZoneId=os.environ["ZONE_ID"],
                        ChangeBatch={"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
                            "Name": name, "Type": "A", "TTL": 60,
                            "ResourceRecords": [{"Value": ip}]}}]})
    else:
        if ec2_state == "running":
            ec2.stop_instances(InstanceIds=[instance_id])
        elif ec2_state == "stopped" and db_state == "available":
            rds.stop_db_instance(DBInstanceIdentifier=db_id)
    if now.year != int(os.environ["HOLIDAY_CALENDAR_YEAR"]):
        raise RuntimeError("Update holiday_calendar_year and holiday_dates; automatic startup disabled")
    return {"desired_running": running, "ec2": ec2_state, "rds": db_state}


def handler(event, context):
    try:
        return reconcile(datetime.now(ZoneInfo("Asia/Tokyo")),
                         boto3.client("ec2"), boto3.client("rds"), boto3.client("route53"))
    except Exception:
        logger.exception("Schedule reconciliation failed; next schedule or manual invocation retries")
        raise
