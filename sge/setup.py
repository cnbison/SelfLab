"""
SGE Package Setup

Phase 3+ 正式 Python 包化（M2.x 一直是 scripts/ 下的临时实现）。

安装（editable）:
    pip install -e sge/

使用:
    from sge import Agent, EventGenerator, SGELLMClient, SGEOrchestrator
"""

from setuptools import setup, find_packages

setup(
    name='sge',
    version='0.1.0',
    description='Self-Generating Engine — AI personality through experience',
    author='Bisen',
    author_email='bison@example.com',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'litellm',
        'pyyaml',
        'python-dotenv',
    ],
    extras_require={
        'dev': [
            'pytest',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
