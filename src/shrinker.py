import datetime

from solver import model, PartitionArena

from z3 import sat, unsat


def test_shrinking(config_generator, max_size, min_size, complex_overlap_constraint):
    print('({:%Y-%m-%d %H:%M:%S}) Starting shrinking test!'.format(datetime.datetime.now()))
    (components, arenas) = config_generator(max_size, complex_overlap_constraint)

    s = model(components, arenas)
    result = s.check()
    if not result == sat:
        raise ValueError("Largest size not large enough! (Result was {})".format(result))
    print("Passed initial check!")

    smallest_working_size = max_size
    largest_failing_size = min_size - 1

    while (smallest_working_size - largest_failing_size) > 1:
        print('({:%Y-%m-%d %H:%M:%S}) Current parameters:'.format(datetime.datetime.now()),
              smallest_working_size, largest_failing_size)

        size_to_check = (smallest_working_size + largest_failing_size) // 2
        (components, arenas) = config_generator(size_to_check, complex_overlap_constraint)
        s = model(components, arenas)
        result = s.check()
        print(result)
        if result == sat:
            smallest_working_size = size_to_check
        elif result == unsat:
            largest_failing_size = size_to_check
        else:
            raise ValueError("s.check() was unknown")
    return smallest_working_size


def check_fragmentation(config_generator):
    (components, arenas) = config_generator(0, False)
    min_size = sum(a.size
                   for a in arenas if isinstance(a, PartitionArena) and a.partition.name == "sram")
    max_size = int(min_size * 1.5)

    print("Min size", min_size, "Max size", max_size)

    # Do shrinking for non complex case
    min_non_complex = test_shrinking(config_generator, max_size, min_size, False)
    print("Min(non_complex)", min_non_complex)

    min_complex = test_shrinking(config_generator, min_non_complex,  min_size, True)
    print("Min(complex)", min_complex)

    print("Overhead(non_complex):", (min_non_complex - min_size) / min_size)
    print("Overhead(complex):", (min_complex - min_size) / min_size)
