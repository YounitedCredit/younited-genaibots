import json
from dataclasses import dataclass
from typing import Any, Dict, List, Union


@dataclass
class Action:
    ActionName: str  # The name of the action
    Parameters: Dict[str, Any]  # The parameters of the action


def normalize_keys(d):
    if isinstance(d, list):
        return [normalize_keys(v) for v in d]
    elif isinstance(d, dict):
        return {(
                    'Action' if k.lower() == 'action' else 'ActionName' if k.lower() == 'actionname' else 'Parameters' if k.lower() == 'parameters' else k): normalize_keys(
            v) for k, v in d.items()}
    else:
        return d


class GenAIResponse():
    def __init__(self, response: List[Action]):
        self.response = response  # The response containing a list of actions

    @classmethod
    async def from_json(cls, json_data: Union[str, Dict[str, Any]]):
        # If the input data is a string, parse it as JSON
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            # If the input data is already a dictionary, use it directly
            data = json_data

        # Normalize keys in data
        data = normalize_keys(data)

        # Check if 'response' is in data
        if 'response' not in data:
            raise ValueError("'response' field is missing in the data")

        actions = []
        for action in data['response']:
            # Check if 'Action' is in each action
            if 'Action' not in action:
                raise ValueError("'Action' field is missing in the action")
            # Create an Action object
            actions.append(Action(**action['Action']))

        # Return an instance of the class with the created actions
        return cls(actions)
