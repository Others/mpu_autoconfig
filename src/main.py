#!/usr/local/bin/python3
from z3 import set_option

from shrinker import check_fragmentation
from vms import \
    configure_setup_with_io_manager, \
    configure_setup_with_io_and_chaining, \
    configure_setup_with_io_and_sharing, \
    setup_config_1, setup_config_2, setup_config_3, setup_config_4, setup_config_5


def kb(x):
    return x * 1024


def mb(x):
    return x * (1024 ** 2)


# def gen_config(size, complex_overlap_constraint):
#     hw_config = HardwareConfig(region_count=3,
#                                subregion_count=8,
#                                complex_overlap_constraint=complex_overlap_constraint)
#
#     server = Component("server", hw_config)
#     client = Component("client", hw_config)
#
#     flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
#     sram = Partition("sram", 0x20000000, 0x20000000 + size)
#
#     server_code = PartitionArena("server/code", flash, kb(10), [server], [])
#     client_code = PartitionArena("client/code", flash, kb(11), [client], [])
#
#     server_main = PartitionArena("server/main", sram, kb(50), [server], [server])
#     client_main = PartitionArena("client/main", sram, kb(30), [client], [client])
#
#     shared = PartitionArena("server+client/shared", sram, kb(25), [server, client],
#                             [server, client])
#
#     components = [server, client]
#     arenas = [server_code, client_code, server_main, client_main, shared]
#
#     return (components, arenas)


def get_setup(i):
    if i == 1:
        return setup_config_1
    elif i == 2:
        return setup_config_2
    elif i == 3:
        return setup_config_3
    elif i == 4:
        return setup_config_4
    elif i == 5:
        return setup_config_5


def get_finalizer(i):
    if i == 1:
        return configure_setup_with_io_manager
    elif i == 2:
        return configure_setup_with_io_and_chaining
    elif i == 3:
        return configure_setup_with_io_and_sharing


if __name__ == '__main__':
    set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)

    print("Enter setup selection (1 - 5):")
    setup = input()

    print("Enter shared memory selection (1 - 3):")
    finalizer = input()

    setup_function = get_setup(setup)
    finalizer_function = get_finalizer(finalizer)

    def config_generator(ram_size, complex_overlap_constraint):
        return finalizer_function(setup_function(ram_size, complex_overlap_constraint))

    check_fragmentation(config_generator)
