from typing import List, Any, Type, Union
from google.protobuf.message import Message
import google.protobuf.timestamp_pb2 as timestamp
from protogen.common.filters_common_pb2 import *


class Filter:
    def message_type(self) -> Type:
        raise NotImplementedError(f"{str(self.__class__.__name__)}.message_type() is not implemented")

    def to_message(self):
        raise NotImplementedError(f"{str(self.__class__.__name__)}.to_message() is not implemented")

    def __bool__(self):
        raise Exception("Filter cannot be converted to bool. Are you trying to use 'and', 'or', 'not' or 'in' instead of '&', '|', '~' or '.contains' ?")

    def to_conjunction(self) -> "FilterConjunction":
        raise NotImplementedError(f"{str(self.__class__.__name__)}.to_conjunction() is not implemented")

    def to_disjunction(self) -> "FilterDisjunction":
        raise NotImplementedError(f"{str(self.__class__.__name__)}.to_disjunction() is not implemented")


class FilterDisjunction(Filter):
    def __init__(self, filters: List["FilterConjunction"]):
        super().__init__()
        self.filters = filters
        _ = self.conjunction_type()
        _ = self.message_type()

    def __or__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        if isinstance(other, SimpleFilter):
            if other.conjunction_type != self.conjunction_type():
                raise Exception(f"Invalid type {type(other).__name__} ({str(other.field)}) for 'or' operand of {self.__class__.__name__} ({str(self)}) : Conjunction types are different")
            return self.__class__(self.filters + [self.conjunction_type()([other])])
        elif isinstance(other, self.conjunction_type()):
            return self.__class__(self.filters + [other])
        elif isinstance(other, self.__class__):
            return self.__class__(self.filters + other.filters)
        raise Exception(f"Invalid type {type(other).__name__} for 'or' operand of {self.__class__.__name__}")

    def __add__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        return self | other

    def __repr__(self):
        return "( " + ' ) or ( '.join([str(f) for f in self.filters]) + ' )'

    def conjunction_type(self) -> Type["FilterConjunction"]:
        raise NotImplementedError(f"{str(self.__class__.__name__)}.conjunction_type() is not implemented")

    def to_message(self):
        raw = self.message_type()()
        setattr(raw, "or", [f.to_message() for f in self.filters])
        return raw

    def to_conjunction(self) -> "FilterConjunction":
        raise Exception("Cannot transform a disjunction into a conjunction")

    def to_disjunction(self) -> "FilterDisjunction":
        return self


class FilterConjunction(Filter):
    def __init__(self, filters: List["SimpleFilter"]):
        super().__init__()
        self.filters = filters
        _ = self.disjunction_type()
        _ = self.message_type()

    def __and__(self, other: Union["SimpleFilter", "FilterConjunction"]) -> "FilterConjunction":
        if isinstance(other, SimpleFilter):
            if other.conjunction_type != self.__class__:
                raise Exception(f"Invalid type {type(other).__name__} ({str(other.field)}) for 'and' operand of {self.__class__.__name__} ({str(self)}) : Conjunction types are different")
            return self.__class__(self.filters + [other])
        elif isinstance(other, self.__class__):
            return self.__class__(self.filters + other.filters)
        raise Exception(f"Invalid type {type(other).__name__} for 'and' operand of {self.__class__.__name__}")

    def __mul__(self, other: Union["SimpleFilter", "FilterConjunction"]) -> "FilterConjunction":
        return self & other

    def __or__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        return self.to_disjunction() | other

    def __add__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        return self | other

    def __repr__(self):
        return ' and '.join([str(f) for f in self.filters])

    def disjunction_type(self) -> Type["FilterDisjunction"]:
        raise NotImplementedError(f"{str(self.__class__.__name__)}.disjunction_type() is not implemented")

    def to_message(self):
        raw = self.message_type()()
        setattr(raw, "and", [f.to_message() for f in self.filters])
        return raw

    def to_conjunction(self) -> "FilterConjunction":
        return self

    def to_disjunction(self) -> "FilterDisjunction":
        return self.disjunction_type()([self])


class SimpleFilter(Filter):
    eq_ = None
    ne_ = None
    lt_ = None
    le_ = None
    gt_ = None
    ge_ = None
    contains_ = None
    notcontains_ = None
    value_type_ = None

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message], value=None, operator=None):
        super().__init__()
        self.field = field
        self.message_type = message_type
        if not issubclass(conjunction_type, FilterConjunction):
            raise Exception(f"{conjunction_type.__name__} is not a subclass of FilterConjunction")
        self.conjunction_type = conjunction_type
        self.inner_message_type = inner_message_type
        self.raw = inner_message_type()
        if value is not None:
            self.raw.value = value
        if operator is not None:
            self.raw.operator = operator

    def __and__(self, other: Union["SimpleFilter", "FilterConjunction"]) -> "FilterConjunction":
        if isinstance(other, SimpleFilter):
            if other.conjunction_type != self.conjunction_type:
                raise Exception(f"Invalid type {type(other).__name__} ({str(other.field)}) for 'and' operand of {self.__class__.__name__} ({str(self.field)}) : Conjunction types are different")
            return self.conjunction_type([self, other])
        elif isinstance(other, self.conjunction_type):
            return other & self
        raise Exception(f"Invalid type {type(other).__name__} for 'and' operand of {self.__class__.__name__}")

    def __mul__(self, other: Union["SimpleFilter", "FilterConjunction"]) -> "FilterConjunction":
        return self & other

    def __or__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        return self.conjunction_type([self]) | other

    def __add__(self, other: Union["SimpleFilter", "FilterConjunction", "FilterDisjunction"]) -> "FilterDisjunction":
        return self | other

    def _verify_value(self, value):
        if self.__class__.value_type_ is None or isinstance(value, self.__class__.value_type_):
            return
        raise Exception(f"Expected value type {str(self.__class__.value_type_)} for field {str(self.field)}, got {str(type(value))} instead")

    def __eq__(self, value):
        return self.check(value, self.__class__.eq_, "==")

    def __ne__(self, value):
        return self.check(value, self.__class__.ne_, "!=")

    def __lt__(self, value):
        return self.check(value, self.__class__.lt_, "<")

    def __le__(self, value):
        return self.check(value, self.__class__.le_, "<=")

    def __gt__(self, value):
        return self.check(value, self.__class__.gt_, ">")

    def __ge__(self, value):
        return self.check(value, self.__class__.lt_, ">=")

    def contains(self, value):
        return self.check(value, self.__class__.contains_, "contains")

    def __invert__(self):
        if self.raw.operator is None:
            raise Exception(f"Cannot invert None operator in class {self.__class__.__name__} for field {str(self.field)}")
        if self.raw.operator == self.__class__.eq_:
            return self.__ne__(self.raw.value)
        if self.raw.operator == self.__class__.ne_:
            return self.__eq__(self.raw.value)
        if self.raw.operator == self.__class__.lt_:
            return self.__ge__(self.raw.value)
        if self.raw.operator == self.__class__.le_:
            return self.__gt__(self.raw.value)
        if self.raw.operator == self.__class__.gt_:
            return self.__le__(self.raw.value)
        if self.raw.operator == self.__class__.ge_:
            return self.__lt__(self.raw.value)
        if self.raw.operator == self.__class__.contains_:
            return self.check(self.raw.value, self.__class__.notcontains_, "not_contains")
        if self.raw.operator == self.__class__.notcontains_:
            return self.contains(self.raw.value)
        raise Exception(f"{self.__class__.__name__} operator {str(self.raw.operator)} for field {str(self.field)} has no inverted equivalent")

    def __neg__(self) -> "SimpleFilter":
        return ~self

    def __repr__(self) -> str:
        return f"{str(self.field)} filter"

    def to_conjunction(self) -> "FilterConjunction":
        return self.conjunction_type([self])

    def to_disjunction(self) -> "FilterDisjunction":
        return self.to_conjunction().to_disjunction()

    def check(self, value: Any, operator: Any, operator_str: str = "") -> "SimpleFilter":
        self._verify_value(value)
        if operator is None:
            raise NotImplementedError(f"Operator {operator_str} is not available for {self.__class__.__name__}")
        return self.__class__(self.field, self.conjunction_type, self.message_type, self.inner_message_type, value, operator)


class StringFilter(SimpleFilter):
    eq_ = FILTER_STRING_OPERATOR_EQUAL
    ne_ = FILTER_STRING_OPERATOR_NOT_EQUAL
    contains_ = FILTER_STRING_OPERATOR_CONTAINS
    notcontains_ = FILTER_STRING_OPERATOR_NOT_CONTAINS
    value_type_ = str

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message] = FilterString, value=None, operator=None):
        super().__init__(field, conjunction_type, message_type, inner_message_type, value, operator)

    def startswith(self, value: str) -> "StringFilter":
        return self.check(value, FILTER_STRING_OPERATOR_STARTS_WITH, "startswith")

    def endswith(self, value: str) -> "StringFilter":
        return self.check(value, FILTER_STRING_OPERATOR_ENDS_WITH, "endswith")

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_string = self.raw
        return message

    def __repr__(self) -> str:
        return f"{str(self.field)} {str(self.raw.operator)} \"{str(self.raw.value)}\""


class StatusFilter(SimpleFilter):
    eq_ = FILTER_STATUS_OPERATOR_EQUAL
    ne_ = FILTER_STATUS_OPERATOR_NOT_EQUAL

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], filter_status_type: Type[Message], value=None, operator=None):
        super().__init__(field, conjunction_type, message_type, filter_status_type, value, operator)

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_status = self.raw
        return message


class DateFilter(SimpleFilter):
    eq_ = FILTER_DATE_OPERATOR_EQUAL
    ne_ = FILTER_DATE_OPERATOR_NOT_EQUAL
    lt_ = FILTER_DATE_OPERATOR_BEFORE
    le_ = FILTER_DATE_OPERATOR_BEFORE_OR_EQUAL
    gt_ = FILTER_DATE_OPERATOR_AFTER
    ge_ = FILTER_DATE_OPERATOR_AFTER_OR_EQUAL
    value_type = timestamp.Timestamp

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message] = FilterDate, value=None, operator=None):
        super().__init__(field, conjunction_type, message_type, inner_message_type, value, operator)

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_date = self.raw
        return message


class NumberFilter(SimpleFilter):
    eq_ = FILTER_NUMBER_OPERATOR_EQUAL
    ne_ = FILTER_NUMBER_OPERATOR_NOT_EQUAL
    lt_ = FILTER_NUMBER_OPERATOR_LESS_THAN
    le_ = FILTER_NUMBER_OPERATOR_LESS_THAN_OR_EQUAL
    gt_ = FILTER_NUMBER_OPERATOR_GREATER_THAN
    ge_ = FILTER_NUMBER_OPERATOR_GREATER_THAN_OR_EQUAL
    value_type_ = int

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message] = FilterNumber, value=None, operator=None):
        super().__init__(field, conjunction_type, message_type, inner_message_type, value, operator)

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_number = self.raw
        return message


class BooleanFilter(SimpleFilter):
    eq_ = FILTER_BOOLEAN_OPERATOR_IS
    value_type_ = bool

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message] = FilterBoolean, value=True, operator=FILTER_BOOLEAN_OPERATOR_IS):
        super().__init__(field, conjunction_type, message_type, inner_message_type, value, operator)

    def __ne__(self, value: bool) -> "BooleanFilter":
        return self.__eq__(not value)

    def __invert__(self):
        return self.__eq__(not self.raw.value)

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_boolean = self.raw
        return message


class ArrayFilter(SimpleFilter):
    contains_ = FILTER_ARRAY_OPERATOR_CONTAINS
    notcontains_ = FILTER_ARRAY_OPERATOR_NOT_CONTAINS
    value_type_ = str

    def __init__(self, field: Message, conjunction_type: Type["FilterConjunction"], message_type: Type[Message], inner_message_type: Type[Message] = FilterArray, value=None, operator=None):
        super().__init__(field, conjunction_type, message_type, inner_message_type, value, operator)

    def to_message(self):
        message = self.message_type()
        message.field = self.field
        message.filter_array = self.raw
        return message
