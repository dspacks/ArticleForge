#!/usr/bin/env python3
"""
Article Processing System — Package setup

Install in development mode:
    pip install -e .

Install normally:
    pip install .

Create standalone executable:
    pip install pyinstaller
    pyinstaller --onefile article-forge
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="article-forge",
    version="1.0.0",
    description="Professional PDF article processing, extraction, and organization system",
    long_description=Path(__file__).parent.joinpath("README.md").read_text(),
    long_description_content_type="text/markdown",
    author="Article Forge Team",
    author_email="noreply@example.com",
    url="https://github.com/example/article-forge",
    license="MIT",

    packages=find_packages(),

    python_requires=">=3.8",
    install_requires=requirements,

    entry_points={
        "console_scripts": [
            "article-forge=__main__:main",
        ],
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business",
        "Topic :: Multimedia",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],

    keywords="pdf articles markdown metadata extraction zotero",

    project_urls={
        "Documentation": "https://github.com/example/article-forge/wiki",
        "Source": "https://github.com/example/article-forge",
        "Tracker": "https://github.com/example/article-forge/issues",
    },
)
