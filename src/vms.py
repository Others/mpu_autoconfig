from solver import Component, HardwareConfig, Partition, PartitionArena


# Helper functions
def kb(x):
    return x * 1024


def mb(x):
    return x * (1024 ** 2)


def gen_component(name, hw_config, flash, sram, text, data):
    comp = Component(name, hw_config)
    arenas = [PartitionArena(name + "/code", flash, text, [comp], []),
              PartitionArena(name + "/main", sram, data, [comp], [comp])]
    return (comp, arenas)


# These create vm functions return (component, arenas) tuples
def vm_basicmath(hw_config, flash, sram):
    return gen_component("basicmath", hw_config, flash, sram, 61961, 12740 + 17260)


def vm_dijkstra(hw_config, flash, sram):
    return gen_component("dijkstra", hw_config, flash, sram, 64256, 12744 + 57708)


def vm_pbmsrch(hw_config, flash, sram):
    return gen_component("pbmsrch", hw_config, flash, sram, 63364, 12744 + 18284)


def vm_rijndael(hw_config, flash, sram):
    return gen_component("rijndael", hw_config, flash, sram, 80576, 12748 + 17260)


def vm_gsm(hw_config, flash, sram):
    return gen_component("gsm", hw_config, flash, sram, 86545, 12932 + 17260)


def vm_big(hw_config, flash, sram):
    return gen_component("big", hw_config, flash, sram, 193512, 12948 + 59244)


# This function sets up the hardware configuration
def get_hardware_configuration(ram_size, complex_overlap_constraint):
    hw_config = HardwareConfig(region_count=8,
                               subregion_count=8,
                               complex_overlap_constraint=complex_overlap_constraint)
    flash = Partition("flash", 0x08000000, 0x08000000 + mb(1))
    sram = Partition("sram", 0x20000000, 0x20000000 + ram_size)
    return hw_config, flash, sram


# These functions create setups of VMs, returning (hw_config, flash, sram, components, arenas) pairs
def setup_config_1(ram_size, complex_overlap_constraint):  # IDEA: Just three small VM
    (hw_config, flash, sram) = get_hardware_configuration(ram_size, complex_overlap_constraint)
    components = []
    all_arenas = []

    (comp, arenas) = vm_basicmath(hw_config, flash, sram)
    components.append(comp)
    all_arenas += arenas

    (comp, arenas) = vm_dijkstra(hw_config, flash, sram)
    components.append(comp)
    all_arenas += arenas

    (comp, arenas) = vm_gsm(hw_config, flash, sram)
    components.append(comp)
    all_arenas += arenas

    return (hw_config, flash, sram, components, all_arenas)


def setup_config_2():  # IDEA: Three small VMs + one big VM
    pass


def setup_config_3():  # IDEA: Four small VMs + one big VM
    pass


def setup_config_4():  # IDEA: Five small VMs
    pass


def setup_config_5():  # IDEA: Five small VMs + one big VM
    pass


# These functions turn a setup into an actual testable configuration
IO_MAN_CODE = 508
IO_MAN_DATA = 4 + 512
SHARED_SIZE = 4096

SCHEDULER_CODE = 508
SCHEDULER_DATA = 4 + 512
SCHEDULER_SHARED = 4096

KERNEL_CODE = 134727
KERNEL_DATA = 158 + 36816


def add_io_manager(config_result):
    (hw_config, flash, sram, components, arenas) = config_result
    io_manager = Component("io_manager", hw_config)
    io_man_code = PartitionArena("io_manager/code", flash, IO_MAN_CODE, [io_manager], [])
    io_man_main = PartitionArena("io_manager/main", sram, IO_MAN_DATA, [io_manager], [io_manager])
    for c in components:
        shared = PartitionArena(c.name + "+io_manager/shared", sram, SHARED_SIZE,
                                [io_manager, c], [io_manager, c])
        arenas.append(shared)
    components.append(io_manager)
    arenas += [io_man_code, io_man_main]
    return (hw_config, flash, sram, components, arenas)


def add_scheduler(config_result):
    (hw_config, flash, sram, components, arenas) = config_result
    scheduler = Component("scheduler", hw_config)
    scheduler_code = PartitionArena("scheduler/code", flash, SCHEDULER_CODE, [scheduler], [])
    scheduler_main = PartitionArena("scheduler/main", sram, SCHEDULER_DATA,
                                    [scheduler], [scheduler])
    components.append(scheduler)
    arenas += [scheduler_code, scheduler_main]
    return (hw_config, flash, sram, components, arenas)


def add_kernel_regions(config_result):
    (hw_config, flash, sram, components, arenas) = config_result
    kernel_code = PartitionArena("kernel/code", flash, KERNEL_CODE, [], [])
    kernel_main = PartitionArena("kernel/main", sram, KERNEL_DATA, [], [])
    arenas += [kernel_code, kernel_main]
    return (hw_config, flash, sram, components, arenas)


def add_chaining(config_result):
    (hw_config, flash, sram, components, arenas) = config_result
    start = None
    prev = None
    for c in components:
        if prev is None:
            start = c
        else:
            shared_region = PartitionArena(c.name + "+" + prev.name + "/shared", sram, SHARED_SIZE,
                                           [prev, c], [prev, c])
            arenas.append(shared_region)
        prev = c
    final_region = PartitionArena(c.name + "+" + prev.name + "/shared", sram, SHARED_SIZE,
                                  [start, prev], [start, prev])
    arenas.append(final_region)
    return (hw_config, flash, sram, components, arenas)


def add_all_shared(config_result):
    (hw_config, flash, sram, components, arenas) = config_result
    for c1 in components:
        for c2 in components:
            if c1 == c2:
                continue
            shared_region = PartitionArena(c1.name + "+" + c2.name + "/shared", sram,
                                           SHARED_SIZE, [c1], [c2])
            arenas.append(shared_region)
    return (hw_config, flash, sram, components, arenas)


def configure_setup_with_io_manager(config_result):
    config_result = add_io_manager(config_result)
    config_result = add_scheduler(config_result)
    config_result = add_kernel_regions(config_result)
    (hw_config, flash, sram, components, arenas) = config_result
    return (components, arenas)


def configure_setup_with_io_and_chaining(config_result):
    config_result = add_chaining(config_result)
    config_result = add_io_manager(config_result)
    config_result = add_scheduler(config_result)
    config_result = add_kernel_regions(config_result)
    (hw_config, flash, sram, components, arenas) = config_result
    return (components, arenas)


def configure_setup_with_io_and_sharing(config_result):
    config_result = add_all_shared(config_result)
    config_result = add_io_manager(config_result)
    config_result = add_scheduler(config_result)
    config_result = add_kernel_regions(config_result)
    (hw_config, flash, sram, components, arenas) = config_result
    return (components, arenas)
