import json


def serialize_packet(packet):
    return json.dumps(packet)


def deserialize_packet(packet_json):
    return json.loads(packet_json)


def update_packet(existing_packet, updates):
    existing_packet.update(updates)
    return existing_packet


def validate_packet(packet):
    required_keys = ['session_id', 'task_chain', 'current_objective']
    return all(key in packet for key in required_keys)
