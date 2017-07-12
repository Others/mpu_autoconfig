#!/usr/local/bin/python3

import z3

REGION_COUNT = 1
SUBREGION_COUNT = 2


# For each component, for each region, create variables:
#   - Start point of the region
#   - Size of the region
#   - Whether each of the subregions is accessible
class Component(object):
    def __init__(self, name):
        self.name = name
        self.regions = []
        for i in range(REGION_COUNT):
            self.regions.append(Region(self.name, i))

    def can_access(self, address):
        predicates = []
        for r in self.regions:
            predicates.append(r.accessible_in_region(address))
        return z3.Or(*predicates)


class Region(object):
    def __init__(self, component, number):
        self.name = component + "/region_" + str(number)
        self.start = z3.BitVec(self.name + "/start_addr", 32)
        self.size = z3.BitVec(self.name + "/size", 32)
        self.subregion_accessibility = []
        for i in range(SUBREGION_COUNT):
            subregion_accessible = z3.Bool(self.name + "/subregion_" + str(i))
            self.subregion_accessibility.append(subregion_accessible)

    def within_subregion(self, address, subregion_number):
        assert subregion_number < SUBREGION_COUNT
        subregion_size = self.size / SUBREGION_COUNT
        subregion_start = self.start + subregion_size * subregion_number
        subregion_end = subregion_start + subregion_size
        return z3.And(address >= z3.BV2Int(subregion_start), address < z3.BV2Int(subregion_end))

    def accessible_in_subregion(self, address, subregion_number):
        assert subregion_number < SUBREGION_COUNT
        accessible = self.subregion_accessibility[subregion_number]
        return z3.And(accessible, self.within_subregion(address, subregion_number))

    def accessible_in_region(self, address):
        predicates = []
        for i in range(SUBREGION_COUNT):
            predicates.append(self.accessible_in_subregion(address, i))
        return z3.Or(*predicates)


# For each area, create variables
#   - Start point of the area
#   - Size variable
class Area(object):
    def __init__(self, name, size, users):
        self.name = name
        self.users = users
        self.start = z3.BitVec(name + "/start_addr", 32)
        self.size_variable = z3.BitVec(name + "/size", 32)
        self.size = size

    def contains(self, address):
        return z3.And(address > z3.BV2Int(self.start), address < z3.BV2Int(self.start + self.size))


def mb(x):
    return x * (1024 ** 2)


def is_pow_of_2(x):
    return (x & (x - 1)) == 0


def bvadd_no_overflow(x, y, signed=False):
    assert x.ctx_ref() == y.ctx_ref()
    # FIXME: Figure out why we might want this
    a, b = x, y  # z3._coerce_exprs(x, y)
    return z3.BoolRef(z3.Z3_mk_bvadd_no_overflow(a.ctx_ref(), a.as_ast(), b.as_ast(), signed))


# components = [Component("server"), Component("client")]
areas = [Area("server/main", mb(128), ["server"]),
         Area("client/main", mb(128), ["client"]),
         Area("server+client/service", mb(8), ["server", "client"])]
components = [Component("server")]
areas = [Area("server/main", 1024, ["server"])]


s = z3.Solver()
# For each address, create constraints:
#   - TODO: Within address space

# For each component, for each region, create constraints:
#   - Size must be a power of two
#   - Size must be divisible by SUBREGION_COUNT
#   - Start point must be a multiple of the size
#   - TODO: Should not overlap with other regions
for c in components:
    for r in c.regions:
        s.add(is_pow_of_2(r.size))
        s.add(r.size % SUBREGION_COUNT == 0)
        s.add(r.start % r.size == 0)

# For each area create constraints:
#   - The size variable is fixed
#   - Adding the size to the start address must not cause an overflow
#   - For every address in this area, every included component must have an accessible subregion
#   - For every address in this area, every other component must NOT have an accessible subregion
for a in areas:
    s.add(a.size_variable == a.size)
    s.add(bvadd_no_overflow(a.start, a.size_variable))

    authorized_components = []
    unauthorized_components = []
    for c in components:
        if c.name in a.users:
            authorized_components.append(c)
        else:
            unauthorized_components.append(c)

    print("area {}:".format(a.name))
    print("\tauthorized_components {}".format(authorized_components))
    print("\tunauthorized_components_components {}".format(unauthorized_components))

    forall_var_count = 0
    for c in authorized_components:
        # Using a different variable each time for saftey
        address = z3.Int("fa_address_" + str(forall_var_count))
        forall_var_count += 1
        # Then doing the check
        s.add(z3.ForAll(address, z3.Or(z3.Not(a.contains(address)), c.can_access(address))))
        # s.add(z3.ForAll(address, z3.Not(a.contains(address))))
    for c in unauthorized_components:
        # Using a different variable each time for saftey
        address = z3.Int("fa_address_" + str(forall_var_count))
        forall_var_count += 1
        # Then doing the check
        s.add(z3.ForAll(address, z3.Not(z3.And(a.contains(address), c.can_access(address)))))

print(s.assertions())
print(s.check())
print(s.model())
