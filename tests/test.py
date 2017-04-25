# coding: utf-8

from __future__ import print_function, unicode_literals, absolute_import, division
import sys
import unittest
import datetime
import time
import gdb
import boost
import boost.detect_version

# Avoiding module 'six' because it might be unavailable
if sys.version_info.major > 2:
    text_type = str
    string_types = str
else:
    text_type = unicode
    string_types = basestring

# Boost version defined in test.cpp
boost_version = boost.detect_version.unpack_boost_version(int(gdb.parse_and_eval('boost_version')) )


def execute_cpp_function(function_name):
    """Run until the end of a specified C++ function (assuming the function has a label 'break_here' at the end)

    :param function_name: C++ function name (str)
    :return: None
    """
    breakpoint_location = '{}:break_here'.format(function_name)
    bp = gdb.Breakpoint(breakpoint_location, internal=True)
    bp.silent = True
    gdb.execute('run')
    assert bp.hit_count == 1
    bp.delete()


class PrettyPrinterTest(unittest.TestCase):
    """Base class for all printer tests"""
    def get_printer_result(self, c_variable_name, children_type=lambda x: x):
        """Get pretty-printer output for C variable with a specified name

        :param c_variable_name: Name of a C variable
        :param children_type: Function to typecast all the children
        :return: (string, [children], display_hint)
        """
        value = gdb.parse_and_eval(c_variable_name)
        pretty_printer = gdb.default_visualizer(value)
        self.assertIsNotNone(pretty_printer, 'Pretty printer was not registred')

        string = pretty_printer.to_string()
        if string is not None:
            string = text_type(string)

        children = [children_type(value) for index, value in pretty_printer.children()] \
                   if hasattr(pretty_printer, 'children') \
                   else None

        if hasattr(pretty_printer, 'display_hint'):
            self.assertIsInstance(pretty_printer.display_hint(), string_types)
            display_hint = text_type(pretty_printer.display_hint())
        else:
            display_hint = None

        # print('string:', string)
        # print('children:', children)
        # print('display_hint:', display_hint)
        return string, children, display_hint

    def __str__(self):
        return '{}.{}'.format(self.__class__.__name__, self._testMethodName)


class IteratorRangeTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_iterator_range')

    def test_empty_range(self):
        string, children, display_hint = self.get_printer_result('empty_range')
        self.assertTrue(string.endswith('of length 0'))
        self.assertEqual(display_hint, 'array')
        self.assertEqual(children, [])

    def test_char_range(self):
        string, children, display_hint = self.get_printer_result('char_range', lambda v: chr(int(v)))
        self.assertTrue(string.endswith('of length 13'))
        self.assertEqual(display_hint, 'array')
        self.assertEqual(children, ['h', 'e', 'l', 'l', 'o', ' ', 'd', 'o', 'l', 'l', 'y', '!', '\0'])


class OptionalTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_optional')

    def test_not_initialized(self):
        string, children, display_hint = self.get_printer_result('not_initialized')
        self.assertTrue(string.endswith('is not initialized'))
        self.assertEqual(children, [])
        self.assertIsNone(display_hint)

    def test_initialized(self):
        string, children, display_hint = self.get_printer_result('ten', int)
        self.assertTrue(string.endswith('is initialized'))
        self.assertEqual(children, [10])
        self.assertIsNone(display_hint, None)


class ReferenceWrapperTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_reference_wrapper')

    def test_int_wrapper(self):
        string, children, display_hint = self.get_printer_result('int_wrapper')
        self.assertEqual(string, '(boost::reference_wrapper<int>) 42')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


class TriboolTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_tribool')

    def test_tribool_false(self):
        string, children, display_hint = self.get_printer_result('val_false')
        self.assertTrue(string.endswith('false'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_tribool_true(self):
        string, children, display_hint = self.get_printer_result('val_true')
        self.assertTrue(string.endswith('true'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_tribool_indeterminate(self):
        string, children, display_hint = self.get_printer_result('val_indeterminate')
        self.assertTrue(string.endswith('indeterminate'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


class ScopedPtrTest(PrettyPrinterTest):
    """Test for scoped_ptr and scoped_array (classes are handled by a single printer)

    Note: printers for scoped_ptr, scoped_array and intrusive_ptr are not really helpful: they only print the address
    of a pointed value. The pointed value should be printed as a child.
    """
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_scoped_ptr')

    def test_scoped_ptr_empty(self):
        string, children, display_hint = self.get_printer_result('scoped_ptr_empty')
        self.assertTrue(string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_scoped_ptr(self):
        string, children, display_hint = self.get_printer_result('scoped_ptr')
        self.assertTrue(not string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_scoped_array_empty(self):
        string, children, display_hint = self.get_printer_result('scoped_array_empty')
        self.assertTrue(string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_scoped_array(self):
        string, children, display_hint = self.get_printer_result('scoped_array')
        self.assertTrue(not string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


@unittest.skipIf(boost_version < (1, 55), 'implemented in boost 1.55 and later')
class IntrusivePtrTest(PrettyPrinterTest):
    """Test for intrusive_ptr

    Note: printers for scoped_ptr, scoped_array and intrusive_ptr are not really helpful: they only print the address
    of a pointed value. The pointed value should be printed as a child.
    """
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_intrusive_ptr')

    def test_intrusive_empty(self):
        string, children, display_hint = self.get_printer_result('intrusive_empty')
        self.assertTrue(string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_intrusive(self):
        string, children, display_hint = self.get_printer_result('intrusive')
        self.assertTrue(not string.endswith('0x0'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


class SharedPtrTest(PrettyPrinterTest):
    """Test for shared_ptr, shared_array and weak_ptr (classes are handled by a single printer)

    Note: printers for shared_ptr, shared_array and weak_ptr are not really helpful: they only print the address
    of a pointed value. The pointed value should be printed as a child.
    """
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_shared_ptr')

    def test_empty_shared_ptr(self):
        string, children, display_hint = self.get_printer_result('empty_shared_ptr')
        self.assertEqual(string, '(boost::shared_ptr<int>) 0x0')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_shared_ptr(self):
        string, children, display_hint = self.get_printer_result('shared_ptr')
        self.assertTrue(string.startswith('(boost::shared_ptr<int>) (count 1, weak count 2)'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_weak_ptr(self):
        string, children, display_hint = self.get_printer_result('weak_ptr')
        self.assertTrue(string.startswith('(boost::weak_ptr<int>) (count 1, weak count 2)'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_empty_shared_array(self):
        string, children, display_hint = self.get_printer_result('empty_shared_array')
        self.assertEqual(string, '(boost::shared_array<int>) 0x0')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_shared_array(self):
        string, children, display_hint = self.get_printer_result('shared_array')
        self.assertTrue(string.startswith('(boost::shared_array<int>) (count 1, weak count 1)'))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


class CircularBufferTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_circular_buffer')

    def test_empty(self):
        string, children, display_hint = self.get_printer_result('empty')
        self.assertTrue(string.endswith('of length 0/3'))
        self.assertEqual(children, [])
        self.assertEqual(display_hint, 'array')

    def test_single_element(self):
        string, children, display_hint = self.get_printer_result('single_element', int)
        self.assertTrue(string.endswith('of length 1/3'))
        self.assertEqual(children, [1])
        self.assertEqual(display_hint, 'array')

    def test_full(self):
        string, children, display_hint = self.get_printer_result('full')
        self.assertTrue(string.endswith('of length 3/3'))
        self.assertEqual(children, [1,2,3])
        self.assertEqual(display_hint, 'array')

    def test_overwrite(self):
        string, children, display_hint = self.get_printer_result('overwrite')
        self.assertTrue(string.endswith('of length 3/3'))
        self.assertEqual(children, [2, 3, 4])
        self.assertEqual(display_hint, 'array')

    def test_reduced_size(self):
        string, children, display_hint = self.get_printer_result('reduced_size')
        self.assertTrue(string.endswith('of length 2/3'))
        self.assertEqual(children, [3, 4])
        self.assertEqual(display_hint, 'array')

class ArrayTest(PrettyPrinterTest):
    # The whole printer is a mess. For an empty array the printer crashes with an
    # exception ("gdb.error: There is no member or method named elems."). The content on an non-array is printed in
    # to_string, children() is not defined.
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_array')

    # def test_empty(self):
    #     string, children, display_hint = self.get_printer_result('empty')
    #     self.assertTrue(string.endswith('of length 0'))
    #     self.assertEqual(children, [])
    #     self.assertEqual(display_hint, 'array')
    #
    # def test_three_elements(self):
    #     string, children, display_hint = self.get_printer_result('three_elements', int)
    #     print('string:', string)
    #     print('children:', children)
    #     print('display_hint:', display_hint)
    #     self.assertTrue(string.endswith('of length 3'))
    #     self.assertEqual(children, [10, 20, 30])
    #     self.assertEqual(display_hint, 'array')


class VariantTest(PrettyPrinterTest):
    # Printing held value as a child would be better
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_variant')

    def test_int_variant(self):
        string, children, display_hint = self.get_printer_result('variant_int')
        self.assertEqual(string, '(boost::variant<...>) which (0) = int value = 42')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_str_variant(self):
        string, children, display_hint = self.get_printer_result('variant_bool')
        self.assertEqual(string, '(boost::variant<...>) which (1) = bool value = true')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


@unittest.skipIf(boost_version < (1, 42, 0), 'implemented in boost 1.42 and later')
class UuidTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_uuid')

    def test_uuid(self):
        string, children, display_hint = self.get_printer_result('uuid')
        self.assertEqual(string, '(boost::uuids::uuid) 01234567-89ab-cdef-0123-456789abcdef')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)


class DateTimeTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_date_time')

    @staticmethod
    def format_ptime(dt):
        # Since ptime is pretty-printed as a local time, we need to convert our datetime to local time first
        local_offset_sec = time.altzone if time.daylight else time.timezone
        dt_local = dt - datetime.timedelta(seconds=local_offset_sec)
        dt_local_str = dt_local.strftime('%Y-%b-%d %H:%M:%S.%f')
        return '(boost::posix_time::ptime) {}'.format(dt_local_str)

    def test_uninitialized_date(self):
        string, children, display_hint = self.get_printer_result('uninitialized_date')
        self.assertEqual(string, '(boost::gregorian::date) uninitialized')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_date(self):
        string, children, display_hint = self.get_printer_result('einstein')
        self.assertEqual(string, '(boost::gregorian::date) 1879-03-14')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_uninitialized_time(self):
        string, children, display_hint = self.get_printer_result('uninitialized_time')
        self.assertEqual(string, '(boost::posix_time::ptime) uninitialized')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_posinfin_time(self):
        string, children, display_hint = self.get_printer_result('pos_infin_time')
        self.assertEqual(string, '(boost::posix_time::ptime) positive infinity')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_neginfin_time(self):
        string, children, display_hint = self.get_printer_result('neg_infin_time')
        self.assertEqual(string, '(boost::posix_time::ptime) negative infinity')
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_time_1970_01_01(self):
        string, children, display_hint = self.get_printer_result('unix_epoch')
        dt = datetime.datetime(year=1970, month=1, day=1)
        self.assertEqual(string, self.format_ptime(dt))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_time_2016_02_11_09_50_45(self):
        string, children, display_hint = self.get_printer_result('ligo')
        dt = datetime.datetime(year=2016, month=2, day=11, hour=9, minute=50, second=45)
        self.assertEqual(string, self.format_ptime(dt))
        self.assertIsNone(children)
        self.assertIsNone(display_hint)

    def test_time_1879_03_14(self):
        # python2:
        #Traceback (most recent call last):
        #   File "test.py", line 367, in test_time3
        #     string, children, display_hint = self.get_printer_result('einstein_time')
        #   File "test.py", line 48, in get_printer_result
        #     string = pretty_printer.to_string()
        #   File "/home/mbalabin/programming/gdb/Boost-Pretty-Printer/boost/printers.py", line 551, in to_string
        #     time_string = datetime.datetime.fromtimestamp(unix_epoch_time).strftime('%Y-%b-%d %H:%M:%S.%f')
        # ValueError: year=1879 is before 1900; the datetime strftime() methods require year >= 1900

        # python3:
        # FAIL: test_time3 (__main__.GregorianDate)
        # ----------------------------------------------------------------------
        # Traceback (most recent call last):
        #   File "test.py", line 370, in test_time3
        #     self.assertEqual(string, self.format_ptime(dt))
        # AssertionError: '(boost::posix_time::ptime) 1879-Mar-14 05:48:48.000000' != '(boost::posix_time::ptime) 1879-Mar-14 07:00:00.000000'
        # - (boost::posix_time::ptime) 1879-Mar-14 05:48:48.000000
        # ?                                         ^ ^^ ^^
        # + (boost::posix_time::ptime) 1879-Mar-14 07:00:00.000000
        # ?

        # todo: Stop using strftime at all. It has numerous problems on various python versions. Switch to isoformat().
        # see also: http://stackoverflow.com/a/32206673
        # string, children, display_hint = self.get_printer_result('einstein_time')
        # dt = datetime.datetime(year=1879, month=3, day=14)
        # self.assertEqual(string, self.format_ptime(dt))
        # self.assertIsNone(children)
        # self.assertIsNone(display_hint)
        pass


@unittest.skipIf(boost_version < (1, 48, 0), 'implemented in boost 1.48 and later')
class FlatSetTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_flat_set')

    def test_empty_set(self):
        string, children, display_hint = self.get_printer_result('empty_set')
        self.assertEqual(string, 'boost::container::flat_set<int> size=0 capacity=0')
        self.assertEqual(children, [])
        self.assertEqual(display_hint, 'array')

    def test_full_set(self):
        string, children, display_hint = self.get_printer_result('fset', int)
        self.assertEqual(string, 'boost::container::flat_set<int> size=2 capacity=4')
        self.assertEqual(children, [1, 2])
        self.assertEqual(display_hint, 'array')

    def test_empty_iter(self):
        string, children, display_hint = self.get_printer_result('uninitialized_iter')
        self.assertEqual(string, None)
        self.assertEqual(children, [])
        self.assertEqual(display_hint, None)

    def test_empty_const_iter(self):
        string, children, display_hint = self.get_printer_result('uninitialized_const_iter')
        self.assertEqual(string, None)
        self.assertEqual(children, [])
        self.assertEqual(display_hint, None)

    def test_iter(self):
        string, children, display_hint = self.get_printer_result('itr', int)
        self.assertEqual(string, None)
        self.assertEqual(children, [2])
        self.assertEqual(display_hint, None)


@unittest.skipIf(boost_version < (1, 48, 0), 'implemented in boost 1.48 and later')
class FlatMapTest(PrettyPrinterTest):
    @classmethod
    def setUpClass(cls):
        execute_cpp_function('test_flat_map')

    def test_empty_map(self):
        string, children, display_hint = self.get_printer_result('empty_map')
        self.assertEqual(string, 'boost::container::flat_map<int, int> size=0 capacity=0')
        self.assertEqual(children, [])
        self.assertEqual(display_hint, 'map')

    def test_map_full(self):
        string, children, display_hint = self.get_printer_result('fmap', int)
        self.assertEqual(string, 'boost::container::flat_map<int, int> size=2 capacity=4')
        self.assertEqual(children, [1, 10, 2, 20])
        self.assertEqual(display_hint, 'map')

    def test_empty_iter(self):
        string, children, display_hint = self.get_printer_result('uninitialized_iter')
        self.assertEqual(string, None)
        self.assertEqual(children, [])
        self.assertEqual(display_hint, None)

    def test_empty_const_iter(self):
        string, children, display_hint = self.get_printer_result('uninitialized_const_iter')
        self.assertEqual(string, None)
        self.assertEqual(children, [])
        self.assertEqual(display_hint, None)

    def test_iter(self):
        string, children, display_hint = self.get_printer_result('itr')
        self.assertEqual(string, None)
        self.assertEqual(len(children), 1)
        self.assertEqual(int(children[0]["first"]), 2)
        self.assertEqual(int(children[0]["second"]), 20)
        self.assertEqual(display_hint, None)


def setUpModule():
    print('*** GDB version:', gdb.VERSION)
    print('*** Python version: {}.{}.{}'.format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))
    print('*** Boost version: {}.{}.{}'.format(*boost_version))
    boost.register_printers()

unittest.main(verbosity=2)
