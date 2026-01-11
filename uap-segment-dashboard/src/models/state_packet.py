class StatePacket:
    def __init__(self):
        self.state = {}

    def update(self, key, value):
        self.state[key] = value

    def get(self, key):
        return self.state.get(key, None)

    def to_json(self):
        import json
        return json.dumps(self.state, indent=4)

    def reset(self):
        self.state = {}