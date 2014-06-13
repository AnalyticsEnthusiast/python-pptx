# encoding: utf-8

"""
Base and meta classes that enable declarative definition of custom element
classes.
"""

from __future__ import absolute_import, print_function

import re

from lxml import etree

from . import etree_parser as oxml_parser
from .ns import NamespacePrefixedTag, qn
from ..util import lazyproperty


def OxmlElement(nsptag_str, nsmap=None):
    """
    Return a 'loose' lxml element having the tag specified by *nsptag_str*.
    *nsptag_str* must contain the standard namespace prefix, e.g. 'a:tbl'.
    The resulting element is an instance of the custom element class for this
    tag name if one is defined.
    """
    nsptag = NamespacePrefixedTag(nsptag_str)
    nsmap = nsmap if nsmap is not None else nsptag.nsmap
    return oxml_parser.makeelement(nsptag.clark_name, nsmap=nsmap)


def serialize_for_reading(element):
    """
    Serialize *element* to human-readable XML suitable for tests. No XML
    declaration.
    """
    xml = etree.tostring(element, encoding='unicode', pretty_print=True)
    return XmlString(xml)


class XmlString(unicode):
    """
    Provides string comparison override suitable for serialized XML that is
    useful for tests.
    """

    # '    <w:xyz xmlns:a="http://ns/decl/a" attr_name="val">text</w:xyz>'
    # |          |                                          ||           |
    # +----------+------------------------------------------++-----------+
    #  front      attrs                                     | text
    #                                                     close

    _xml_elm_line_patt = re.compile(
        '( *</?[\w:]+)(.*?)(/?>)([^<]*</[\w:]+>)?'
    )

    def __eq__(self, other):
        lines = self.splitlines()
        lines_other = other.splitlines()
        if len(lines) != len(lines_other):
            return False
        for line, line_other in zip(lines, lines_other):
            if not self._eq_elm_strs(line, line_other):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def _attr_seq(self, attrs):
        """
        Return a sequence of attribute strings parsed from *attrs*. Each
        attribute string is stripped of whitespace on both ends.
        """
        attrs = attrs.strip()
        attr_lst = attrs.split()
        return sorted(attr_lst)

    def _eq_elm_strs(self, line, line_2):
        """
        Return True if the element in *line_2* is XML equivalent to the
        element in *line*.
        """
        front, attrs, close, text = self._parse_line(line)
        front_2, attrs_2, close_2, text_2 = self._parse_line(line_2)
        if front != front_2:
            return False
        if self._attr_seq(attrs) != self._attr_seq(attrs_2):
            return False
        if close != close_2:
            return False
        if text != text_2:
            return False
        return True

    def _parse_line(self, line):
        """
        Return front, attrs, close, text 4-tuple result of parsing XML element
        string *line*.
        """
        match = self._xml_elm_line_patt.match(line)
        front, attrs, close, text = [match.group(n) for n in range(1, 5)]
        return front, attrs, close, text


class MetaOxmlElement(type):
    """
    Metaclass for BaseOxmlElement
    """
    def __init__(cls, clsname, bases, clsdict):
        for key, value in clsdict.items():
            if isinstance(value, ZeroOrOne):
                value.populate_class_members(cls, key)


class _BaseChildElement(object):
    """
    Base class for the child element classes corresponding to varying
    cardinalities, such as ZeroOrOne and ZeroOrMore.
    """
    def __init__(self, nsptagname, successors=()):
        super(_BaseChildElement, self).__init__()
        self._nsptagname = nsptagname
        self._successors = successors

    def populate_class_members(self, element_cls, prop_name):
        """
        Baseline behavior for adding the appropriate methods to
        *element_cls*.
        """
        self._element_cls = element_cls
        self._prop_name = prop_name

    def _add_adder(self):
        """
        Add an ``_add_x()`` method to the element class for this child
        element.
        """
        def _add_child(obj, **attrs):
            new_method = getattr(obj, self._new_method_name)
            child = new_method()
            for key, value in attrs.items():
                setattr(child, key, value)
            insert_method = getattr(obj, self._insert_method_name)
            insert_method(child)
            return child

        _add_child.__doc__ = (
            'Add a new ``<%s>`` child element unconditionally, inserted in t'
            'he correct sequence.' % self._nsptagname
        )
        self._add_to_class(self._add_method_name, _add_child)

    def _add_creator(self):
        """
        Add a ``_new_{prop_name}()`` method to the element class that creates
        a new, empty element of the correct type, having no attributes.
        """
        creator = self._creator
        creator.__doc__ = (
            'Return a "loose", newly created ``<%s>`` element having no attri'
            'butes, text, or children.' % self._nsptagname
        )
        self._add_to_class(self._new_method_name, creator)

    def _add_getter(self):
        """
        Add a read-only ``{prop_name}`` property to the element class for
        this child element.
        """
        property_ = property(self._getter, None, None)
        # assign unconditionally to overwrite element name definition
        setattr(self._element_cls, self._prop_name, property_)

    def _add_inserter(self):
        """
        Add an ``_insert_x()`` method to the element class for this child
        element.
        """
        def _insert_child(obj, child):
            obj.insert_element_before(child, *self._successors)

        _insert_child.__doc__ = (
            'Insert the passed ``<%s>`` element as a child in the correct se'
            'quence.' % self._nsptagname
        )
        self._add_to_class(self._insert_method_name, _insert_child)

    @lazyproperty
    def _add_method_name(self):
        return '_add_%s' % self._prop_name

    def _add_to_class(self, name, method):
        """
        Add *method* to the target class as *name*, unless *name* is already
        defined on the class.
        """
        if hasattr(self._element_cls, name):
            return
        setattr(self._element_cls, name, method)

    @property
    def _creator(self):
        """
        Return a function object that creates a new, empty element of the
        right type, having no attributes.
        """
        def new_child_element(obj):
            return OxmlElement(self._nsptagname)
        return new_child_element

    @property
    def _getter(self):
        """
        Return a function object suitable for the "get" side of the property
        descriptor.
        """
        def get_child_element(obj):
            return obj.find(qn(self._nsptagname))
        get_child_element.__doc__ = (
            '``<%s>`` child element or |None| if not present.'
            % self._nsptagname
        )
        return get_child_element

    @lazyproperty
    def _insert_method_name(self):
        return '_insert_%s' % self._prop_name

    @lazyproperty
    def _remove_method_name(self):
        return '_remove_%s' % self._prop_name

    @lazyproperty
    def _new_method_name(self):
        return '_new_%s' % self._prop_name


class ZeroOrOne(_BaseChildElement):
    """
    Defines an optional child element for MetaOxmlElement.
    """
    def populate_class_members(self, element_cls, prop_name):
        """
        Add the appropriate methods to *element_cls*.
        """
        super(ZeroOrOne, self).populate_class_members(element_cls, prop_name)
        self._add_getter()
        self._add_creator()
        self._add_inserter()
        self._add_adder()
        self._add_get_or_adder()
        self._add_remover()

    def _add_get_or_adder(self):
        """
        Add a ``get_or_add_x()`` method to the element class for this
        child element.
        """
        def get_or_add_child(obj):
            child = getattr(obj, self._prop_name)
            if child is None:
                add_method = getattr(obj, self._add_method_name)
                child = add_method()
            return child
        get_or_add_child.__doc__ = (
            'Return the ``<%s>`` child element, newly added if not present.'
        ) % self._nsptagname
        self._add_to_class(self._get_or_add_method_name, get_or_add_child)

    def _add_remover(self):
        """
        Add a ``_remove_x()`` method to the element class for this child
        element.
        """
        def _remove_child(obj):
            obj.remove_all(self._nsptagname)
        _remove_child.__doc__ = (
            'Remove all ``<%s>`` child elements.'
        ) % self._nsptagname
        self._add_to_class(self._remove_method_name, _remove_child)

    @lazyproperty
    def _get_or_add_method_name(self):
        return 'get_or_add_%s' % self._prop_name


class BaseOxmlElement(etree.ElementBase):
    """
    Provides common behavior for oxml element classes
    """

    __metaclass__ = MetaOxmlElement

    @classmethod
    def child_tagnames_after(cls, tagname):
        """
        Return a sequence containing the namespace prefixed child tagnames,
        e.g. 'a:prstGeom', that occur after *tagname* in this element.
        """
        return cls.child_tagnames.tagnames_after(tagname)

    def first_child_found_in(self, *tagnames):
        """
        Return the first child found with tag in *tagnames*, or None if
        not found.
        """
        for tagname in tagnames:
            child = self.find(qn(tagname))
            if child is not None:
                return child
        return None

    def insert_element_before(self, elm, *tagnames):
        successor = self.first_child_found_in(*tagnames)
        if successor is not None:
            successor.addprevious(elm)
        else:
            self.append(elm)
        return elm

    def remove_all(self, tagname):
        """
        Remove all child elements having *tagname*.
        """
        matching = self.findall(qn(tagname))
        for child in matching:
            self.remove(child)

    def remove_if_present(self, *tagnames):
        """
        Remove all child elements having tagname in *tagnames*.
        """
        for tagname in tagnames:
            element = self.find(qn(tagname))
            if element is not None:
                self.remove(element)

    @property
    def xml(self):
        """
        Return XML string for this element, suitable for testing purposes.
        Pretty printed for readability and without an XML declaration at the
        top.
        """
        return serialize_for_reading(self)
