
from setuptools import setup
from transmitm import __version__


setup(name='transmitm',
      version=__version__,
      description='Transport layer transparent intercepting proxy.',
      long_description_content_type='text/markdown',
      long_description=open('README.md').read().strip(),
      author='Daniel Timofte @tim17d',
      author_email='timofte.daniel@tuta.io',
      url='https://github.com/tsundokul/transmitm',
      py_modules=['transmitm'],
      install_requires=['twisted>=20.3'],
      license='MIT License',
      keywords='transparent mitm man-in-the-middle proxy',
      packages=['transmitm'],
      setup_requires=["wheel"],
      python_requires='>=3.5',
      classifiers=[
         "Development Status :: 4 - Beta",
         "Topic :: System :: Networking",
         "Topic :: System :: Networking :: Monitoring",
         "Topic :: Security",
         "Operating System :: POSIX :: Linux",
         "Operating System :: Microsoft :: Windows",
         "License :: OSI Approved :: MIT License",
         'Programming Language :: Python :: 3',
      ]
      # options={
      #     'bdist_wheel': {'python_tag': 'cp30', 'py_limited_api': 'cp32'},
      #     'build_ext': {'build_lib': 'pyradamsa/lib'}
      # }
   )
