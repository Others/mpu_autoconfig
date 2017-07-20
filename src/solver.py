#!/usr/local/bin/python3

from abc import ABC

import z3
from z3 import And, Bool, BitVec, BitVecRef, ForAll, Not, Or, UGE, ULE

# TODO: Put these into a "HardwareConfig" class
REGION_MIN_SIZE = 256
REGION_COUNT = 3
SUBREGION_COUNT = 1


def ULT(a, b):
    if isinstance(a, BitVecRef) or isinstance(b, BitVecRef):
        return z3.ULT(a, b)
    return a < b


def is_pow_of_2(x):
    return (x & (x - 1)) == 0


class Component(object):
    def __init__(self, name):
        self.name = name
        self.regions = []
        for i in range(REGION_COUNT):
            self.regions.append(Region(self, i))

    def is_consistent(self):
        # TODO: Add constraint that regions don't overlap
        region_consistency = []
        for r in self.regions:
            region_consistency += r.is_consistent()
        return region_consistency

    def can_read(self, addr):
        region_readiblity = []
        for r in self.regions:
            region_readiblity.append(r.can_read(addr))
        return Or(*region_readiblity)

    def can_write(self, addr):
        region_writeablity = []
        for r in self.regions:
            region_writeablity.append(r.can_write(addr))
        return Or(*region_writeablity)


class Region(object):
    def __init__(self, owner, number):
        self.owner = owner
        self.name = self.owner.name + "/r_" + str(number)
        self.start = BitVec(self.name + "/start", 32)
        self.size = BitVec(self.name + "/size", 32)
        self.end = self.start + self.size
        subregion_size = self.size / SUBREGION_COUNT
        self.subregions = []
        for i in range(SUBREGION_COUNT):
            start = self.start + i * subregion_size
            self.subregions.append(Subregion(self, i, start, start + subregion_size))
        self.readable = Bool(self.name + "/can_read")
        self.writeable = Bool(self.name + "/can_write")

    def is_consistent(self):
        return [ULT(self.start, self.end),  is_pow_of_2(self.size),
                self.size % SUBREGION_COUNT == 0, self.start % self.size == 0,
                UGE(self.size, REGION_MIN_SIZE)]

    def is_enabled(self, addr):
        subregion_enabled = []
        for sr in self.subregions:
            subregion_enabled.append(sr.is_enabled(addr))
        return Or(*subregion_enabled)

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

    def is_consistent(self):
        return [ULT(self.start, self.end)]

    def contains(self, addr):
        return And(ULE(self.start, addr), ULT(addr, self.end))

    def access_consistent(self, all_components):
        constraints = []

        for r in self.readers:
            constraints.append(self.readable_by(r))

        non_readers = filter(lambda c: c not in self.readers, all_components)
        for r in non_readers:
            constraints.append(Not(self.readable_by(r)))

        for r in self.writers:
            constraints.append(self.writeable_by(r))

        non_writers = filter(lambda c: c not in self.writers, all_components)
        for r in non_writers:
            constraints.append(Not(self.writeable_by(r)))
        return constraints

    def readable_by(self, component):
        addr = BitVec("addr", 32)
        return ForAll(addr, z3.And(self.contains(addr), component.can_read(addr)))

    def writeable_by(self, component):
        addr = BitVec("addr", 32)
        return ForAll(addr, z3.And(self.contains(addr), component.can_write(addr)))


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

# components = [Component("server")]
# areas = [Area("server/main", 1024, ["server"])]


def model(components, arenas):
    s = z3.Solver()

    for c in components:
        print (c.is_consistent())
        s.add(*c.is_consistent())

    # TODO: Add constraint that arenas don't overlap
    for a in arenas:
        s.add(*a.is_consistent())
        s.add(*a.access_consistent(components))

    return s
