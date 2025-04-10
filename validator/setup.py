#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="abcd-validator",
    version="0.1.0",
    description="ABCD XML Validator Tool",
    author="Your Organization",
    author_email="your.email@example.com",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "lxml",
        "requests",
        "psutil",
        "PyYAML",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
