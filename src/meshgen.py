import math


def calculate_3d_mesh_config(total_tets: int, tets_per_block: int) -> tuple[int, int, int]:
    if total_tets % tets_per_block != 0:
        raise ValueError('total_tets must be divisible by tets_per_block')

    wanted_blocks = math.ceil(total_tets / tets_per_block)
    configs = []

    # using max_side_length = math.ceil(wanted_blocks ** (1 / 3)) doesn't work because math.ceil sometimes enforces side lengths greater than max_side_lengths
    for x in range(1, wanted_blocks + 1):
        yRest = math.ceil(wanted_blocks / x)
        for y in range(x, yRest):
            zRest = math.ceil(yRest / y)
            for z in range(y, zRest + 1):
                n = x * y * z * tets_per_block
                if n == total_tets:
                    configs.append((x, y, z))

    if len(configs) == 0:
        raise AssertionError("No mesh config found")

    most_balanced_config = configs[-1]
    balance = abs(max(most_balanced_config) - min(most_balanced_config))

    for c in configs[-2:-1:-1]:
        c_balance = abs(max(c) - min(c))

        if c_balance < balance:
            most_balanced_config = c
            balance = c_balance

    return most_balanced_config
