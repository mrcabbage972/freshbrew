model_name_map = {"Deepseek V3": "DeepSeek-V3", "Gpt 4.1": "GPT-4.1", "Gpt 4O": "GPT-4o", "O3 Mini": "o3-mini"}


def get_model_name(model_name):
    return model_name_map.get(model_name, model_name)
