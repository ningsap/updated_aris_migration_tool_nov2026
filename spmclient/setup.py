from setuptools import setup, find_packages

setup(
    name='spm-client',
    url='https://github.com/Signavio-Consulting/spmclient',
    author='Maximilian Rau',
    author_email='maximilian.rau@signavio.com',
    packages=['spm'],
    install_requires=['requests', 'PyYAML'],
    version='0.4',
    description='Central Python package covering Signavio Process Manager API requests',
    # long_description=open('README.txt').read(),
)