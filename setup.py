from setuptools import setup

setup(name='rpmdeplint',
      version='1.0',
      description='RPM Dependency Graph Analysis',
      url='https://gerrit.beaker-project.org/rpmdeplint',
      author='Red Hat, Inc.',
      author_email='jorris@redhat.com',
      license='LGPLv2.1',
      packages=['rpmdeplint'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
)
