from setuptools import setup, find_packages


setup(
    name="pav",
    version="1.2.0",
    author="Arian",
    author_email="ariannasiri86@gmail.com",
    description="PAV is a Python library with features to easily work with venv",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ArianN8610/PAV",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["click"],
    entry_points={"console_scripts": ["pav=pav.cli:main"]}
)
