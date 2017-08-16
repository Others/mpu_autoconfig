#!/usr/local/bin/python3

from abc import ABC

import z3
from z3 import And, Bool, BitVec, Exists, ForAll, Implies, Not, Or, UGE, ULE


def ULT(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return a < b
    return z3.ULT(a, b)


def is_pow_of_2(x):
    return (x & (x - 1)) == 0


def overlap(r1, r2):
    return And(ULT(r1.start, r2.end), ULT(r2.start, r1.end))


def any_overlap(ranges):
    predicates = []
    already_checked = []
    for r1 in ranges:
        for r2 in already_checked:
            predicates.append(overlap(r1, r2))
        already_checked.append(r1)
    return Or(predicates)


class HardwareConfig(object):
    def __init__(self, region_min_size=256, region_count=8, subregion_count=8):
        self.region_min_size = region_min_size
        self.region_count = region_count
        self.subregion_count = subregion_count


class Component(object):
    def __init__(self, name, hw_config):
        self.name = name
        self.hw_config = hw_config
        self.regions = []
        for i in range(hw_config.region_count):
            self.regions.append(Region(self, i, hw_config))

    def __repr__(self):
        return "Component({}, {})".format(self.name, self.hw_config)

    def is_consistent(self):
        # Regions cannot overlap
        self_consistency = [Not(any_overlap(self.regions))]
        region_consistency = []
        for r in self.regions:
            region_consistency += r.is_consistent()
        return self_consistency + region_consistency

    def can_read(self, addr):
        region_readiblity = []
        for r in self.regions:
            region_readiblity.append(r.can_read(addr))
        return Or(region_readiblity)

    def can_write(self, addr):
        region_writeablity = []
        for r in self.regions:
            region_writeablity.append(r.can_write(addr))
        return Or(region_writeablity)


class Region(object):
    def __init__(self, owner, number, hw_config):
        self.owner = owner
        self.name = self.owner.name + "/r_" + str(number)
        self.hw_config = hw_config

        self.start = BitVec(self.name + "/start", 32)
        self.size = BitVec(self.name + "/size", 32)
        self.end = self.start + self.size
        subregion_size = self.size / hw_config.subregion_count
        self.subregions = []
        for i in range(hw_config.subregion_count):
            start = self.start + i * subregion_size
            self.subregions.append(Subregion(self, i, start, start + subregion_size))
        self.readable = Bool(self.name + "/can_read")
        self.writeable = Bool(self.name + "/can_write")

    def is_consistent(self):
        return [ULT(self.start, self.end),
                is_pow_of_2(self.size),
                self.size % self.hw_config.subregion_count == 0,
                self.start % self.size == 0,
                UGE(self.size, self.hw_config.region_min_size)]

    def is_enabled(self, addr):
        subregion_enabled = []
        for sr in self.subregions:
            subregion_enabled.append(sr.is_enabled(addr))
        return Or(subregion_enabled)

    def can_read(self, addr):
        return And(self.readable, self.is_enabled(addr))

    def can_write(self, addr):
        return And(self.writeable, self.is_enabled(addr))


class Subregion(object):
    def __init__(self, owner, number, start, end):
        self.owner = owner
        self.name = self.owner.name + "/sr_" + str(number)
        self.start = start
        self.end = end
        self.enabled = Bool(self.name + "/enabled")

    def is_enabled(self, addr):
        return And(self.enabled, ULE(self.start, addr), ULT(addr, self.end))


class Partition(object):
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end


class Arena(ABC):
    def __init__(self, name, start, end, readers, writers):
        self.name = name
        self.start = start
        self.end = end
        self.readers = readers
        self.writers = writers

    def __repr__(self):
        return "Arena({}, {}, {})".format(self.name, self.start, self.end)

    def is_consistent(self):
        return [ULT(self.start, self.end)]

    def contains(self, addr):
        return And(ULE(self.start, addr), ULT(addr, self.end))

    def access_consistent(self, all_components):
        constraints = []

        for r in self.readers:
            constraints.append(self.readable_by(r))

        non_readers = list(filter(lambda c: c not in self.readers, all_components))
        for nr in non_readers:
            constraints.append(self.not_readable_by(nr))

        for w in self.writers:
            constraints.append(self.writeable_by(w))

        non_writers = list(filter(lambda c: c not in self.writers, all_components))
        for nw in non_writers:
            constraints.append(self.not_writeable_by(nw))
        return constraints

    def readable_by(self, component):
        addr = new_addr()
        return ForAll(addr, Implies(self.contains(addr), component.can_read(addr)))

    def not_readable_by(self, component):
        addr = new_addr()
        return Not(Exists(addr, And(self.contains(addr), component.can_read(addr))))

    def writeable_by(self, component):
        addr = new_addr()
        return ForAll(addr, Implies(self.contains(addr), component.can_write(addr)))

    def not_writeable_by(self, component):
        addr = new_addr()
        return Not(Exists(addr, And(self.contains(addr), component.can_write(addr))))


count = -1


def new_addr():
    global count
    count += 1
    return BitVec("addr({})".format(count), 32)


class PartitionArena(Arena):
    def __init__(self, name, partition, size, readers, writers):
        self.partition = partition
        start = BitVec(name + "/start", 32)
        super().__init__(name, start, start + size, readers, writers)

    def is_consistent(self):
        return super().is_consistent() + [ULE(self.partition.start, self.start),
                                          ULT(self.end, self.partition.end)]


class FixedArena(Arena):
    def __init__(self, name, start, end, readers, writers):
        super().__init__(name, start, end, readers, writers)


def model(components, arenas):
    s = z3.Solver()

    for c in components:
        s.add(*c.is_consistent())

    for a in arenas:
        s.add(a.is_consistent())
        s.add(a.access_consistent(components))

    # Arenas can't overlap
    s.add(Not(any_overlap(arenas)))

    return s
