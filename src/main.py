#!/usr/local/bin/python3

from z3 import sat, set_option, unsat
from solver import Component, HardwareConfig, Partition, PartitionArena, model


def kb(x):
    return x * 1024


def mb(x):
    return x * (1024 ** 2)


if __name__ == '__main__':
    # Prevent truncated output
    set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)

    # hw_config = HardwareConfig(region_count=2, subregion_count=1)
    # component = Component("server")
    #
    # flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
    # sram = Partition("sram", 0x20000000, 0x20000000 + kb(512))
    #
    # component_code = PartitionArena("component/code", flash, kb(10), [component], [])
    # component_main = PartitionArena("component/main", sram, kb(50), [component], [component])
    #
    # components = [component]
    # arenas = [component_code, component_main]

    hw_config = HardwareConfig(region_count=3, subregion_count=1)

    server = Component("server", hw_config)
    client = Component("client", hw_config)

    flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
    sram = Partition("sram", 0x20000000, 0x20000000 + kb(512))

    server_code = PartitionArena("server/code", flash, kb(10), [server], [])
    client_code = PartitionArena("client/code", flash, kb(11), [client], [])

    server_main = PartitionArena("server/main", sram, kb(50), [server], [server])
    client_main = PartitionArena("client/main", sram, kb(20), [client], [client])

    shared = PartitionArena("server+client/shared", sram, kb(1), [server, client], [server, client])

    components = [server, client]
    arenas = [server_code, client_code, server_main, client_main, shared]

    s = model(components, arenas)

    print(s.assertions())

    check_result = s.check()
    print(check_result)
    if check_result == sat:
        print(s.model())
    elif check_result == unsat:
        print(s.unsat_core())
