from app.admin import settings

USAGE = {}

def showGia(rate=26_442.43):
    total_usd = sum(model["cost"] for model in USAGE.values())
    total_vnd = total_usd * rate
    
    print(USAGE)
    print(f"Tổng chi phí: {total_usd:.8f} USD ≈ {total_vnd:,.2f} VND")
    
def calc_cost(model: str, input_tokens: int, output_tokens: int):
    price = settings.PRICING[model]
    unit = price["unit_token"]

    cost_in = (input_tokens / unit) * price["input"]
    cost_out = (output_tokens / unit) * price["output"]

    return cost_in, cost_out

def update_usage(model: str, input_tokens: int, output_tokens: int):
    cost_in, cost_out = calc_cost(model, input_tokens, output_tokens)
    total_cost = cost_in + cost_out

    if model not in USAGE:
        USAGE[model] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        }

    USAGE[model]["input_tokens"] += input_tokens
    USAGE[model]["output_tokens"] += output_tokens
    USAGE[model]["cost"] += total_cost
