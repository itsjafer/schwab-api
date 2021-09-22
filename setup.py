from distutils.core import setup
import os.path
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="schwab_api",
    packages=setuptools.find_packages(),
    version="0.2.0",
    license="MIT",
    description="Unofficial Schwab API wrapper in Python 3.",
    author="Jafer Haider",
    author_email="itsjafer@gmail.com",
    url="https://github.com/itsjafer/schwab-api",
    long_description=long_description,
    long_description_content_type="text/markdown",
    download_url="https://github.com/itsjafer/schwab-api/tarball/master",
    keywords=["schwab", "python3", "api", "unofficial", "schwab-api", "schwab charles api"],
    install_requires=["playwright", "playwright-stealth", "pyotp", "python-vipaccess"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)