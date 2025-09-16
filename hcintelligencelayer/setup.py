from setuptools import setup, find_packages

setup(
    name='hcintelligencelayer',
    version='0.1.0',
    maintainer='CareHaven-AI Team',
    description='A plug-and-play architecture for healthcare intelligence layer.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/your-username/healthcare-intelligence-core',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Healthcare Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
    python_requires='>=3.7',
    install_requires=[
        # Add your project's dependencies here
        # e.g., 'pandas', 'numpy', 'scikit-learn'
    ],
    extras_require={
        'dev': [
            # Dependencies for development and testing
            'pytest',
            'flake8',
            'pylint',
        ]
    }
)