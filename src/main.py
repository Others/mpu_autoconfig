#!/usr/local/bin/python3
import datetime

from z3 import sat, set_option, unsat

from solver import Component, HardwareConfig, Partition, PartitionArena, model


def kb(x):
    return x * 1024


def mb(x):
    return x * (1024 ** 2)


def gen_config(size, complex_overlap_constraint):
    # hw_config = HardwareConfig(region_count=2, subregion_count=1)
    # component1 = Component("component1", hw_config)
    # component2 = Component("component2", hw_config)
    #
    # flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
    # sram = Partition("sram", 0x20000000, 0x20000000 + size)
    #
    # component1_code = PartitionArena("component1/code", flash, kb(10), [component1], [])
    # component1_main = PartitionArena("component1/main", sram, kb(50) + 5, [component1],
    #                                  [component1])
    #
    # component2_code = PartitionArena("component2/code", flash, kb(10), [component2], [])
    # component2_main = PartitionArena("component2/main", sram, kb(50) + 7, [component2],
    #                                  [component2])
    #
    # components = [component1, component2]
    # arenas = [component1_code, component1_main, component2_code, component2_main]

    hw_config = HardwareConfig(region_count=3,
                               subregion_count=8,
                               complex_overlap_constraint=complex_overlap_constraint)

    server = Component("server", hw_config)
    client = Component("client", hw_config)

    flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
    sram = Partition("sram", 0x20000000, 0x20000000 + size)

    server_code = PartitionArena("server/code", flash, kb(10), [server], [])
    client_code = PartitionArena("client/code", flash, kb(11), [client], [])

    server_main = PartitionArena("server/main", sram, kb(50), [server], [server])
    client_main = PartitionArena("client/main", sram, kb(30), [client], [client])

    shared = PartitionArena("server+client/shared", sram, kb(25), [server, client],
                            [server, client])

    components = [server, client]
    arenas = [server_code, client_code, server_main, client_main, shared]

    return (components, arenas)


def test_shrinking(max_size, min_size, complex_overlap_constraint):
    print('({:%Y-%m-%d %H:%M:%S}) Starting shrinking test!'.format(datetime.datetime.now()))
    (components, arenas) = gen_config(max_size, complex_overlap_constraint)

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
        (components, arenas) = gen_config(size_to_check, complex_overlap_constraint)
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


def check_fragmentation(max_size):
    (components, arenas) = gen_config(max_size, False)
    min_size = sum(a.size
                   for a in arenas if isinstance(a, PartitionArena) and a.partition.name == "sram")

    print("Min size", min_size, "Max size", max_size)

    # Do shrinking for non complex case
    min_non_complex = test_shrinking(max_size, min_size, False)
    print("Min(non_complex)", min_non_complex)

    min_complex = test_shrinking(min_non_complex,  min_size, True)
    print("Min(complex)", min_complex)

    print("Overhead(non_complex):", (min_non_complex - min_size) / min_size)
    print("Overhead(complex):", (min_complex - min_size) / min_size)


if __name__ == '__main__':
    # Prevent truncated output
    set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)

    check_fragmentation(112641)

    # smallest_working_size = test_shrinking(kb(1000))
    # print("Smallest working size", smallest_working_size)
    #
    # (components, arenas) = gen_config(smallest_working_size)
    # s = model(components, arenas)
    #
    # print(s.assertions())
    #
    # check_result = s.check()
    # print(check_result)
    # if check_result == sat:
    #     print(s.model())
    # elif check_result == unsat:
    #     print(s.unsat_core())
