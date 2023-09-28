from setuptools import find_packages, setup

setup(name='cvc5tools',
      version='0.1.0',
      description='Tools to help you test cvc5',
      author='Leni Aniva',
      author_email='aniva@stanford.edu',
      packages=find_packages(),
      install_requires=["pandas"],
      )
