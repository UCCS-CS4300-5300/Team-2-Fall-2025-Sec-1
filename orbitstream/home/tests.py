from django.test import TestCase

# Create your tests here.

from django.test import TestCase
from home.utils import dummy_function, add_numbers, subtract_numbers
from home.models import DummyModel

"""dummy tests"""

"""
From the project root (where manage.py is):
pytest --cov=home --maxfail=1 --disable-warnings -q --cov-report=term-missing --cov-fail-under=80
"""

class DummyFunctionTest(TestCase):
    def test_dummy_function(self):
        assert dummy_function() is True

    def test_add_numbers(self):
        assert add_numbers(2, 3) == 5

    def test_subtract_numbers(self):
        assert subtract_numbers(5, 3) == 2  # add this line


class DummyModelTest(TestCase):
    def test_create_model(self):
        obj = DummyModel(name="Test")
        self.assertEqual(str(obj), "Test")