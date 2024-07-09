
from core.genai_interactions.genai_cost_base import GenAICostBase


def test_genai_cost_base_initialization():
    # Create an instance of GenAICostBase with specific values
    cost_base = GenAICostBase(
        total_tk=1000,
        prompt_tk=300,
        completion_tk=700,
        input_token_price=0.01,
        output_token_price=0.02
    )

    # Verify that the values are correctly assigned
    assert cost_base.total_tk == 1000
    assert cost_base.prompt_tk == 300
    assert cost_base.completion_tk == 700
    assert cost_base.input_token_price == 0.01
    assert cost_base.output_token_price == 0.02

def test_genai_cost_base_attribute_modification():
    # Create an instance with initial default values
    cost_base = GenAICostBase()

    # Modify the attributes
    cost_base.total_tk = 2000
    cost_base.prompt_tk = 600
    cost_base.completion_tk = 1400
    cost_base.input_token_price = 0.03
    cost_base.output_token_price = 0.04

    # Verify that the values have been correctly modified
    assert cost_base.total_tk == 2000
    assert cost_base.prompt_tk == 600
    assert cost_base.completion_tk == 1400
    assert cost_base.input_token_price == 0.03
    assert cost_base.output_token_price == 0.04
