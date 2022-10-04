from setuptools import find_packages, setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name="pology",
    version="0.12",
    author="Chusslove Illich",
    author_email="caslav.ilic@gmx.net",
    description=("Python library and collection of command-line tools for "
                 "in-depth processing of PO files"),
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="http://pology.nedohodnik.net/",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
