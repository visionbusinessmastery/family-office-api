user_memory = {}

def get_memory(user_email):
    return user_memory.get(user_email, {
        "history": [],
        "last_allocation": None,
        "last_score": None
    })


def update_memory(user_email, data):
    if user_email not in user_memory:
        user_memory[user_email] = {}

    user_memory[user_email].update(data)
