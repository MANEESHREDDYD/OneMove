import argparse
import json
import logging
import sys
from datetime import datetime
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("dlq_operator")

def _get_dlq_subscription_path(project_id: str, env: str) -> str:
    return f"projects/{project_id}/subscriptions/zonepilot-opt-dead-letter-sub-{env}"

def _get_primary_topic_path(project_id: str, env: str) -> str:
    return f"projects/{project_id}/topics/zonepilot-opt-jobs-{env}"

def inspect_dlq(project_id: str, env: str, limit: int = 10):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = _get_dlq_subscription_path(project_id, env)
    
    logger.info(f"Inspecting DLQ: {subscription_path}")
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": limit},
        timeout=10.0
    )
    
    if not response.received_messages:
        logger.info("DLQ is empty.")
        return

    for received_message in response.received_messages:
        msg = received_message.message
        logger.info("==================================================")
        logger.info(f"Message ID: {msg.message_id}")
        logger.info(f"Publish Time: {msg.publish_time}")
        logger.info(f"Attributes: {msg.attributes}")
        
        # Do NOT log the raw data blindly; just size or a sanitized snippet
        size = len(msg.data)
        logger.info(f"Payload Size: {size} bytes")
        try:
            parsed = json.loads(msg.data.decode("utf-8"))
            # Mask potentially sensitive fields before printing
            safe_keys = list(parsed.keys())
            logger.info(f"Payload Keys: {safe_keys}")
        except json.JSONDecodeError:
            logger.warning("Payload is not valid JSON (poison payload).")
        
        # Return the message to the queue (NACK) so it isn't lost during inspection
        subscriber.modify_ack_deadline(
            request={
                "subscription": subscription_path,
                "ack_ids": [received_message.ack_id],
                "ack_deadline_seconds": 0,
            }
        )

def replay_dlq(project_id: str, env: str, message_id: str, operator: str, reason: str):
    subscriber = pubsub_v1.SubscriberClient()
    publisher = pubsub_v1.PublisherClient()
    subscription_path = _get_dlq_subscription_path(project_id, env)
    topic_path = _get_primary_topic_path(project_id, env)
    
    logger.info(f"Seeking Message {message_id} in {subscription_path} for Replay")
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": 100},
        timeout=10.0
    )
    
    for rm in response.received_messages:
        if rm.message.message_id == message_id:
            # Replay the message
            logger.info(f"Found message {message_id}. Replaying to {topic_path}...")
            # Audit log
            audit = {
                "action": "REPLAY",
                "message_id": message_id,
                "original_publish_time": str(rm.message.publish_time),
                "operator": operator,
                "reason": reason,
                "action_time": datetime.utcnow().isoformat() + "Z"
            }
            logger.info(f"AUDIT_RECORD: {json.dumps(audit)}")
            
            future = publisher.publish(topic_path, rm.message.data, **rm.message.attributes, dlq_replayed="true")
            new_msg_id = future.result()
            logger.info(f"Replay successful. New Message ID: {new_msg_id}")
            
            # ACK the old one
            subscriber.acknowledge(
                request={"subscription": subscription_path, "ack_ids": [rm.ack_id]}
            )
            return
        else:
            # NACK others
            subscriber.modify_ack_deadline(
                request={
                    "subscription": subscription_path,
                    "ack_ids": [rm.ack_id],
                    "ack_deadline_seconds": 0,
                }
            )
    
    logger.error(f"Message {message_id} not found in current DLQ pull batch.")

def discard_dlq(project_id: str, env: str, message_id: str, operator: str, reason: str, classification: str):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = _get_dlq_subscription_path(project_id, env)
    
    logger.info(f"Seeking Message {message_id} in {subscription_path} for Discard")
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": 100},
        timeout=10.0
    )
    
    for rm in response.received_messages:
        if rm.message.message_id == message_id:
            audit = {
                "action": "DISCARD",
                "message_id": message_id,
                "original_publish_time": str(rm.message.publish_time),
                "operator": operator,
                "reason": reason,
                "classification": classification,
                "action_time": datetime.utcnow().isoformat() + "Z"
            }
            logger.info(f"AUDIT_RECORD: {json.dumps(audit)}")
            
            # ACK to discard
            subscriber.acknowledge(
                request={"subscription": subscription_path, "ack_ids": [rm.ack_id]}
            )
            logger.info(f"Message {message_id} permanently discarded.")
            return
        else:
            # NACK others
            subscriber.modify_ack_deadline(
                request={
                    "subscription": subscription_path,
                    "ack_ids": [rm.ack_id],
                    "ack_deadline_seconds": 0,
                }
            )
    
    logger.error(f"Message {message_id} not found in current DLQ pull batch.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OneMove DLQ Operator Tool")
    parser.add_argument("action", choices=["inspect", "replay", "discard"])
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--env", required=True, choices=["staging", "production"], help="Environment")
    parser.add_argument("--limit", type=int, default=10, help="Max messages to inspect")
    parser.add_argument("--msg-id", help="Message ID for replay/discard")
    parser.add_argument("--operator", help="Operator username/email")
    parser.add_argument("--reason", help="Reason for action")
    parser.add_argument("--classification", help="Defect classification (e.g. POISON, EXHAUSTED)")

    args = parser.parse_args()

    if args.action == "inspect":
        inspect_dlq(args.project, args.env, args.limit)
    elif args.action == "replay":
        if not all([args.msg_id, args.operator, args.reason]):
            logger.error("--msg-id, --operator, and --reason are required for replay.")
            sys.exit(1)
        replay_dlq(args.project, args.env, args.msg_id, args.operator, args.reason)
    elif args.action == "discard":
        if not all([args.msg_id, args.operator, args.reason, args.classification]):
            logger.error("--msg-id, --operator, --reason, and --classification are required for discard.")
            sys.exit(1)
        discard_dlq(args.project, args.env, args.msg_id, args.operator, args.reason, args.classification)
