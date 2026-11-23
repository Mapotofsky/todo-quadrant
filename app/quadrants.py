"""任务象限与显示名称。"""

QUADRANTS = {
    0: {"name": "重要·紧急", "important": 1, "urgent": 1},
    1: {"name": "重要·不紧急", "important": 1, "urgent": 0},
    2: {"name": "不重要·紧急", "important": 0, "urgent": 1},
    3: {"name": "不重要·不紧急", "important": 0, "urgent": 0},
}

_QMAP = {(1, 1): 0, (1, 0): 1, (0, 1): 2, (0, 0): 3}


def quadrant_of(important, urgent):
    return _QMAP[(bool(important), bool(urgent))]
