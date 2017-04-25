# encoding: utf-8

# Pretty-printers for Boost (http://www.boost.org)

# Copyright (C) 2009 Rüdiger Sonderfeld <ruediger@c-plusplus.de>
# Copyright (C) 2014 Matei David <matei@cs.toronto.edu>

# Boost Software License - Version 1.0 - August 17th, 2003

# Permission is hereby granted, free of charge, to any person or organization
# obtaining a copy of the software and accompanying documentation covered by
# this license (the "Software") to use, reproduce, display, distribute,
# execute, and transmit the Software, and to prepare derivative works of the
# Software, and to permit third-parties to whom the Software is furnished to
# do so, all subject to the following:

# The copyright notices in the Software and this entire statement, including
# the above license grant, this restriction and the following disclaimer,
# must be included in all copies of the Software, in whole or in part, and
# all derivative works of the Software, unless such copies or derivative
# works are solely in the form of machine-executable object code generated by
# a source language processor.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

#
# Inspired _but not copied_ from libstdc++'s pretty printers
#

import datetime
import re
from .utils import *


###
### Individual Printers follow.
###
### Relevant fields:
###
### - 'printer_name' : Subprinter name used by gdb. (Required.) If it contains
###     regex operators, they must be escaped when refering to it from gdb.
### - 'version' : Appended to the subprinter name. (Required.)
### - 'supports(GDB_Value_Wrapper)' classmethod : If it exists, it is used to
###     determine if the Printer supports the given object.
### - 'template_name' : string or list of strings. Only objects with this
###     template name will attempt to use this printer.
###     (Either supports() or template_name is required.)
### - '__init__' : Its only argument is a GDB_Value_Wrapper.
###

@add_printer
class BoostIteratorRange:
    "Pretty Printer for boost::iterator_range (Boost.Range)"
    printer_name = 'boost::iterator_range'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::iterator_range'

    class _iterator:
        def __init__(self, begin, end):
            self.item = begin
            self.end = end
            self.count = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.item == self.end:
                raise StopIteration
            count = self.count
            self.count = self.count + 1
            elem = self.item.dereference()
            self.item = self.item + 1
            return ('[%d]' % count, elem)

        def next(self):
            return self.__next__()

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def children(self):
        return self._iterator(self.value['m_Begin'], self.value['m_End'])

    def to_string(self):
        begin = self.value['m_Begin']
        end = self.value['m_End']
        return '%s of length %d' % (self.typename, int(end - begin))

    def display_hint(self):
        return 'array'

@add_printer
class BoostOptional:
    "Pretty Printer for boost::optional (Boost.Optional)"
    printer_name = 'boost::optional'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::optional'
    regex = re.compile('^boost::optional<(.*)>$')

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    class _iterator:
        def __init__(self, member, empty):
            self.member = member
            self.done = empty

        def __iter__(self):
            return self

        def __next__(self):
            if(self.done):
                raise StopIteration
            self.done = True
            return ('value', self.member.dereference())

        def next(self):
            return self.__next__()

    def children(self):
        initialized = self.value['m_initialized']
        if(not initialized):
            return self._iterator('', True)
        else:
            match = BoostOptional.regex.search(self.typename)
            if match:
                try:
                    membertype = lookup_type(match.group(1)).pointer()
                    member = self.value['m_storage']['dummy_']['data'].address.cast(membertype)
                    return self._iterator(member, False)
                except:
                    return self._iterator('', True)

    def to_string(self):
        initialized = self.value['m_initialized']
        if(not initialized):
            return "%s is not initialized" % self.typename
        else:
            return "%s is initialized" % self.typename

@add_printer
class BoostReferenceWrapper:
    "Pretty Printer for boost::reference_wrapper (Boost.Ref)"
    printer_name = 'boost::reference_wrapper'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::reference_wrapper'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        return '(%s) %s' % (self.typename, self.value['t_'].dereference())

@add_printer
class BoostTribool:
    "Pretty Printer for boost::logic::tribool (Boost.Tribool)"
    printer_name = 'boost::logic::tribool'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::logic::tribool'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        state = self.value['value']
        s = 'indeterminate'
        if(state == 0):
            s = 'false'
        elif(state == 1):
            s = 'true'
        return '(%s) %s' % (self.typename, s)

@add_printer
class BoostScopedPtr:
    "Pretty Printer for boost::scoped/intrusive_ptr/array (Boost.SmartPtr)"
    printer_name = 'boost::scoped/intrusive_ptr/array'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = ['boost::intrusive_array', 'boost::intrusive_ptr',
                     'boost::scoped_array', 'boost::scoped_ptr']

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        return '(%s) %s' % (self.typename, self.value['px'])

@add_printer
class BoostSharedPtr:
    "Pretty Printer for boost::shared/weak_ptr/array (Boost.SmartPtr)"
    printer_name = 'boost::shared/weak_ptr/array'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = ['boost::shared_array', 'boost::shared_ptr',
                     'boost::weak_array', 'boost::weak_ptr']

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        if self.value['px'] == 0x0:
            return '(%s) %s' % (self.typename, self.value['px'])
        countobj = self.value['pn']['pi_'].dereference()
        refcount = countobj['use_count_']
        weakcount = countobj['weak_count_']
        return '(%s) (count %d, weak count %d) %s' % (self.typename,
                                                      refcount, weakcount,
                                                      self.value['px'])

@add_printer
class BoostCircular:
    "Pretty Printer for boost::circular_buffer (Boost.Circular)"
    printer_name = 'boost::circular_buffer'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::circular_buffer'

    class _iterator:
        def __init__(self, first, last, buff, end, size):
            self.item = first # virtual beginning of the circular buffer
            self.last = last  # virtual end of the circular buffer (one behind the last element).
            self.buff = buff  # internal buffer used for storing elements in the circular buffer
            self.end = end    # internal buffer's end (end of the storage space).
            self.size = size
            self.capa = int(end-buff)
            self.count = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.count == self.size:
                raise StopIteration
            count = self.count
            crt=self.buff + (count + self.item - self.buff) % self.capa
            elem = crt.dereference()
            self.count = self.count + 1
            return ('[%d]' % count, elem)
            #
            # dead code
            #
            if self.item == self.last:
                raise StopIteration
            count = self.count
            self.count = self.count + 1
            elem = self.item.dereference()
            self.item = self.item + 1
            if self.item == self.end:
                self.item == self.buff
            return ('[%d]' % count, elem)

        def next(self):
            return self.__next__()

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def children(self):
        return self._iterator(self.value['m_first'], self.value['m_last'], self.value['m_buff'], self.value['m_end'], self.value['m_size'])

    def to_string(self):
        first = self.value['m_first']
        last = self.value['m_last']
        buff = self.value['m_buff']
        end = self.value['m_end']
        size = self.value['m_size']
        return '%s of length %d/%d' % (self.typename, int(size), int(end-buff))

    def display_hint(self):
        return 'array'

@add_printer
class BoostArray:
    "Pretty Printer for boost::array (Boost.Array)"
    printer_name = 'boost::array'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::array'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        return self.value['elems']

    def display_hint(self):
        return 'array'

@add_printer
class BoostVariant:
    "Pretty Printer for boost::variant (Boost.Variant)"
    printer_name = 'boost::variant'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::variant'
    regex = re.compile('^boost::variant<(.*)>$')

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        m = BoostVariant.regex.search(self.typename)
        types = [s.strip() for s in re.split(r', (?=(?:<[^>]*?(?: [^>]*)*))|, (?=[^>,]+(?:,|$))', m.group(1))]
        which = intptr(self.value['which_'])
        type = types[which]
        data = ''
        try:
            ptrtype = lookup_type(type).pointer()
            data = self.value['storage_']['data_']['buf'].address.cast(ptrtype)
        except:
            data = self.value['storage_']['data_']['buf']
        return '(boost::variant<...>) which (%d) = %s value = %s' % (which,
                                                                     type,
                                                                     data.dereference())

@add_printer
class BoostUuid:
    "Pretty Printer for boost::uuids::uuid (Boost.Uuid)"
    printer_name = 'boost::uuids::uuid'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::uuids::uuid'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        u = (int(self.value['data'][i]) for i in xrange(16))
        s = 'xxxx-xx-xx-xx-xxxxxx'.replace('x', '%02x') % tuple(u)
        return '(%s) %s' % (self.typename, s)


@add_printer
class BoostGregorianDate:
    "Pretty Printer for boost::gregorian::date"
    printer_name = 'boost::gregorian::date'
    min_supported_version = (1, 40, 0)
    max_supported_version = last_supported_boost_version
    template_name = 'boost::gregorian::date'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        n = intptr(self.value['days_'])
        date_int_type_bits = self.value['days_'].type.sizeof * 8
        # Compatibility fix for gdb+python2, which erroneously converts big 64-bit unsigned
        # values to negative python ints. It affects various special values and dates in VERY distant future.
        if n < 0:
            n += 2**date_int_type_bits

        # Check for uninitialized case
        if n == 2**date_int_type_bits - 2:
            return '(%s) uninitialized' % self.typename
        # Convert date number to year-month-day
        a = n + 32044
        b = (4*a + 3) // 146097
        c = a - (146097*b) // 4
        d = (4*c + 3) // 1461
        e = c - (1461*d) // 4
        m = (5*e + 2) // 153
        day = e + 1 - (153*m + 2) // 5
        month = m + 3 - 12*(m // 10)
        year = 100*b + d - 4800 + (m // 10)
        return '(%s) %4d-%02d-%02d' % (self.typename, year, month, day)

@add_printer
class BoostPosixTimePTime:
    "Pretty Printer for boost::posix_time::ptime"
    printer_name = 'boost::posix_time::ptime'
    min_supported_version = (1, 40)
    max_supported_version = (1, 60)
    template_name = 'boost::posix_time::ptime'

    def __init__(self, value):
        self.typename = value.type_name
        self.value = value

    def to_string(self):
        n = int(self.value['time_']['time_count_']['value_'])
        # Check for uninitialized case
        if n==2**63-2:
            return '(%s) uninitialized' % self.typename
        # Check for boost::posix_time::pos_infin case
        if n==2**63-1:
            return '(%s) positive infinity' % self.typename
        # Check for boost::posix_time::neg_infin case
        if n==-2**63:
            return '(%s) negative infinity' % self.typename
        # Subtract the unix epoch from the timestamp and convert the resulting timestamp into something human readable
        unix_epoch_time = (n-210866803200000000)/1000000.0
        time_string = datetime.datetime.fromtimestamp(unix_epoch_time).strftime('%Y-%b-%d %H:%M:%S.%f')
        return '(%s) %s' % (self.typename, time_string)
