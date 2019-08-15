from setuptools import setup, find_packages

setup(
    name='molgenis-python-client-demo',
    author='Mariska Slofstra',
    version='1.0',
    description='Demo of the Python client for the MOLGENIS REST API',
    url='https://github.com/molgenis/molgenis-python-client-demo/',
    license='GNU Lesser General Public License 3.0',
    packages=find_packages(),
    install_requires=['molgenis-py-client>=2.1.0', 'termcolor==1.1.0', 'yaspin>=0.14.3', 'natsort==6.0.0',
                      'names==0.3.0'],
)
