import setuptools

required_packages=[
        'numpy',
        'pyserial',
        'bitstring',
        'pycryptodomex',
        'pyyaml',
        'rospkg',
        'ipython',
        'py3rosmsgs',
        'jinja2<3.1',
        'pytest',
        'pandas',
        'setuptools-scm',
        'importlib-resources',
        'kaleido',
        'plotly',
        'dash'
        ]

setuptools.setup(
    name='bagpy',
    packages=setuptools.find_packages(),
    install_requires=required_packages,
    )