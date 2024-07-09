from core.backend.pricing_data import PricingData


def test_pricing_data_initialization():
    # Create an instance of PricingData with specific values
    pricing = PricingData(
        total_tokens=100,
        prompt_tokens=50,
        completion_tokens=50,
        total_cost=20.0,
        input_cost=10.0,
        output_cost=10.0
    )

    # Verify that the values are correctly assigned
    assert pricing.total_tokens == 100
    assert pricing.prompt_tokens == 50
    assert pricing.completion_tokens == 50
    assert pricing.total_cost == 20.0
    assert pricing.input_cost == 10.0
    assert pricing.output_cost == 10.0

def test_pricing_data_attribute_modification():
    # Create an instance with initial default values
    pricing = PricingData()

    # Modify the attributes
    pricing.total_tokens = 200
    pricing.prompt_tokens = 100
    pricing.completion_tokens = 100
    pricing.total_cost = 40.0
    pricing.input_cost = 20.0
    pricing.output_cost = 20.0

    # Verify that the values have been correctly modified
    assert pricing.total_tokens == 200
    assert pricing.prompt_tokens == 100
    assert pricing.completion_tokens == 100
    assert pricing.total_cost == 40.0
    assert pricing.input_cost == 20.0
    assert pricing.output_cost == 20.0
