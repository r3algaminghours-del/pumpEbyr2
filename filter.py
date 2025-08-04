def is_promising(info):
    mc = info.get("marketCap", 0)
    dev_hold = info.get("devTokenPercentage", 100)
    return mc < 50000 and dev_hold < 5
