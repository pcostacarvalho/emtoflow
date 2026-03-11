def read_file(name):

    with open(name, "r") as f:
        lines = f.readlines()

    return lines