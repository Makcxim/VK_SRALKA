import json
import os
import random

from decouple import config


def validate_group_id(group_id: int):
    """Validates group_id"""
    if not group_id:
        group_id = config.get("VK_TEST_GROUP_ID")
        if not group_id:
            raise ValueError("No group_id provided")
    return group_id


def custom_serializer(obj):
    """Custom serializer for json.dumps() to handle bytes to str conversion"""
    if isinstance(obj, str):
        return obj.encode("utf-8").decode("unicode-escape")
    return obj


def random_delay(a: int = 5, b: int = 10):
    """Returns random delay between a and b"""
    return random.randint(a, b)


def create_if_not_exists_groups_json():
    """
    Create groups.json file if not exists
    Checks if file is empty and writes empty dict if so
    """
    file_path = 'groups.json'

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump({}, file, ensure_ascii=False, default=custom_serializer)

