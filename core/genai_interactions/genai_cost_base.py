class GenAICostBase:
    def __init__(self, total_tk=None, prompt_tk=None, completion_tk=None, input_token_price=None,
                 output_token_price=None):
        self.total_tk = total_tk
        self.prompt_tk = prompt_tk
        self.completion_tk = completion_tk
        self.input_token_price = input_token_price
        self.output_token_price = output_token_price
