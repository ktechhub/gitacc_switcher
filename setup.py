"""Setup script for gitacc-switcher package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="gitacc-switcher",
    version="0.1.0",
    description="Git Account Switcher - Manage multiple Git SSH accounts easily",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/ktechhub/gitacc-switcher",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies required
    ],
    entry_points={
        "console_scripts": [
            "gitacc=gitacc_switcher.cli:main",
        ],
    },
    keywords="git ssh account switcher multiple accounts",
    project_urls={
        "Bug Reports": "https://github.com/ktechhub/gitacc-switcher/issues",
        "Source": "https://github.com/ktechhub/gitacc-switcher",
    },
)
