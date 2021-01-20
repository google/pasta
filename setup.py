# coding=utf-8
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from setuptools import setup, find_packages

import unittest

def all_tests():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('.', pattern='*_test.py')
    return test_suite

setup(
    name="google-pasta",
    version="0.2.0",
    packages=find_packages(),

    # metadata for upload to PyPI
    author="Nick Smith",
    author_email="smithnick@google.com",
    description="pasta is an AST-based Python refactoring library",
    license="Apache 2.0",
    keywords="python refactoring ast",
    url="https://github.com/google/pasta",
    test_suite='setup.all_tests',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: Apache Software License",
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    install_requires=[
        'six',
    ],
)
