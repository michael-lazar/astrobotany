def ordinal_format(value):
    # https://stackoverflow.com/a/50992575
    n = int(value)
    suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    return str(n) + suffix
