def SQUARE(number: int):
    return number * number

def CUBE(number: int):
    return number * number * number

def EXP_SLOW(number: int):
    return int((5 * CUBE(number)) / 4)

def EXP_FAST(number: int):
    return int((4 * CUBE(number)) / 5)

def EXP_MEDIUM_FAST(number: int):
    return int(CUBE(number))

def EXP_MEDIUM_SLOW(number: int):
    return int((6 * CUBE(number)) / 5 - (15 * SQUARE(number)) + (100 * number) - 140)

def EXP_ERRATIC(number: int):
    if number <= 50:
        return int((100 - number) * CUBE(number) / 50)
    if number <= 68:
        return int((150 - number) * CUBE(number) / 100)
    if number <= 98:
        return int(((1911 - 10 * number) / 3) * CUBE(number) / 500)
    return int((160 - number) * CUBE(number) / 100)

def EXP_FLUCTUATING(number: int):
    if number <= 15:
        return int(((number + 1) / 3 + 24) * CUBE(number) / 50)
    if number <= 36:
        return int((number + 14) * CUBE(number) / 50)
    return int(((number / 2) + 32) * CUBE(number) / 50)

def PERCENT_FEMALE(percent: float):
    return int(min(254.0, ((percent * 255) / 100)))