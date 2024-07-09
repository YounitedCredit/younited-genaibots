class PricingData:
    def __init__(self, total_tokens=0, prompt_tokens=0, completion_tokens=0, total_cost=0, input_cost=0, output_cost=0):
        self.total_tokens = total_tokens
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_cost = total_cost
        self.input_cost = input_cost
        self.output_cost = output_cost
