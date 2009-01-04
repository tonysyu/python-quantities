﻿"""
"""

import copy

import numpy

from quantities.dimensionality import BaseDimensionality, \
    MutableDimensionality, ImmutableDimensionality
from quantities.registry import unit_registry

def prepare_compatible_units(s, o):
    try:
        ss, os = s.simplified, o.simplified
        assert ss.units == os.units
        return ss, os
    except AssertionError:
        raise ValueError(
            'can not compare quantities with units of %s and %s'\
            %(ss.units, os.units)
        )


class QuantityIterator:

    """an iterator for quantity objects"""

    def __init__(self, object):
        self.object = object
        self.iterator = super(Quantity, object).__iter__()

    def __iter__(self):
        return self

    def next(self):
        return Quantity(self.iterator.next(), self.object.units)


class Quantity(numpy.ndarray):

    # TODO: what is an appropriate value?
    __array_priority__ = 21

    def __new__(cls, data, units='', dtype='d', mutable=True):
        if not isinstance(data, numpy.ndarray):
            data = numpy.array(data, dtype=dtype)

        data = data.copy()

        if isinstance(data, Quantity) and units:
            if isinstance(units, BaseDimensionality):
                units = str(units)
            data = data.rescale(units)

        ret = numpy.ndarray.__new__(
            cls,
            data.shape,
            data.dtype,
            buffer=data
        )
        ret.flags.writeable = mutable
        return ret

    def __init__(self, data, units='', dtype='d', mutable=True):
        if isinstance(data, Quantity) and not units:
            dims = data.dimensionality
        elif isinstance(units, str):
            if units == '': units = 'dimensionless'
            dims = unit_registry[units].dimensionality
        elif isinstance(units, Quantity):
            dims = units.dimensionality
        elif isinstance(units, (BaseDimensionality, dict)):
            dims = units
        else:
            assert units is None
            dims = None

        self._mutable = mutable
        if self.is_mutable:
            if dims is None: dims = {}
            self._dimensionality = MutableDimensionality(dims)
        else:
            if dims is None:
                self._dimensionality = None
            else:
                self._dimensionality = ImmutableDimensionality(dims)

    @property
    def dimensionality(self):
        if self._dimensionality is None:
            return ImmutableDimensionality({self:1})
        else:
            return ImmutableDimensionality(self._dimensionality)

    @property
    def magnitude(self):
        return self.view(type=numpy.ndarray)

    @property
    def is_mutable(self):
        return self._mutable

    # get and set methods for the units property
    def get_units(self):
        return str(self.dimensionality)
    def set_units(self, units):
        if not self.is_mutable:
            raise AttributeError("can not modify protected units")
        if isinstance(units, str):
            units = unit_registry[units]
        if isinstance(units, Quantity):
            try:
                assert units.magnitude == 1
            except AssertionError:
                raise ValueError('units must have unit magnitude')
        try:
            sq = Quantity(1.0, self.dimensionality).simplified
            osq = units.simplified
            assert osq.dimensionality == sq.dimensionality
            self.magnitude.flat[:] *= sq.magnitude.flat[:] / osq.magnitude.flat[:]
            self._dimensionality = \
                MutableDimensionality(units.dimensionality)
        except AssertionError:
            raise ValueError(
                'Unable to convert between units of "%s" and "%s"'
                %(sq.units, osq.units)
            )
    units = property(get_units, set_units)

    def rescale(self, units):
        """
        Return a copy of the quantity converted to the specified units
        """
        copy = Quantity(self)
        copy.units = units
        return copy

    @property
    def simplified(self):
        rq = self.magnitude * unit_registry['dimensionless']
        for u, d in self.dimensionality.iteritems():
            rq = rq * u.reference_quantity**d
        return rq

    def __array_finalize__(self, obj):
        self._dimensionality = getattr(
            obj, 'dimensionality', MutableDimensionality()
        )

#    def __deepcopy__(self, memo={}):
#        dimensionality = copy.deepcopy(self.dimensionality)
#        return self.__class__(
#            self.view(type=ndarray),
#            self.dtype,
#            dimensionality
#        )

#    def __cmp__(self, other):
#        raise

    def __add__(self, other):
        if self.dimensionality:
            assert isinstance(other, Quantity)
        dims = self.dimensionality + other.dimensionality
        magnitude = self.magnitude + other.magnitude
        return Quantity(magnitude, dims, magnitude.dtype)

    def __sub__(self, other):
        if self.dimensionality:
            assert isinstance(other, Quantity)
        dims = self.dimensionality - other.dimensionality
        magnitude = self.magnitude - other.magnitude
        return Quantity(magnitude, dims, magnitude.dtype)

    def __mul__(self, other):
        assert isinstance(other, (numpy.ndarray, int, float))
        try:
            dims = self.dimensionality * other.dimensionality
            magnitude = self.magnitude * other.magnitude
        except:
            dims = copy.copy(self.dimensionality)
            magnitude = self.magnitude * other
        return Quantity(magnitude, dims, magnitude.dtype)

    def __truediv__(self, other):
        assert isinstance(other, (numpy.ndarray, int, float))
        try:
            dims = self.dimensionality / other.dimensionality
            magnitude = self.magnitude / other.magnitude
        except:
            dims = copy.copy(self.dimensionality)
            magnitude = self.magnitude / other
        return Quantity(magnitude, dims, magnitude.dtype)

    __div__ = __truediv__

    def __rmul__(self, other):
        # TODO: This needs to be properly implemented
        return self.__mul__(other)

    def __rtruediv__(self, other):
        return other * self**-1

    __rdiv__ = __rtruediv__

    def __pow__(self, other):
        assert isinstance(other, (numpy.ndarray, int, float))
        dims = self.dimensionality**other
        magnitude = self.magnitude**other
        return Quantity(magnitude, dims, magnitude.dtype)

    def __repr__(self):
        return '%s*%s'%(numpy.ndarray.__str__(self), self.units)

    __str__ = __repr__

    def __getitem__(self, key):
        return Quantity(self.magnitude[key], self.units)

    def __setitem__(self, key, value):
        self.magnitude[key] = value.rescale(self.units).magnitude

    def __iter__(self):
        return QuantityIterator(self)

    def __lt__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude < os.magnitude

    def __le__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude <= os.magnitude

    def __eq__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude == os.magnitude

    def __ne__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude != os.magnitude

    def __gt__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude > os.magnitude

    def __ge__(self, other):
        ss, os = prepare_compatible_units(self, other)
        return ss.magnitude >= os.magnitude
