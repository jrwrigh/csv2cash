import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="csv2cash",
    version="0.2.5",
    author="u2berggeist",
    description="Module to process CSV and import into GNUCash",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/u2berggeist/csv2cash",
    packages=setuptools.find_packages()
)
