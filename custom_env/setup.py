from setuptools import setup, find_packages

setup(
    name='custom_env',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'pyresparser==1.0.6',
    ],
    package_data={
        '': ['pyresparser/*'],
    },
    include_package_data=True,
)
