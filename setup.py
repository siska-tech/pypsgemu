#!/usr/bin/env python3
"""
AY-3-8910 PSG Emulator - Setup Script

Pythonパッケージ設定ファイル
"""

from setuptools import setup, find_packages
import os

# README.mdを読み込み
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "AY-3-8910 PSG Emulator - A complete software emulation of the AY-3-8910 sound chip"

# 依存関係を定義
INSTALL_REQUIRES = [
    'numpy>=1.19.0',
    'matplotlib>=3.3.0',
    'sounddevice>=0.4.0',
    'psutil>=5.7.0',
]

EXTRAS_REQUIRE = {
    'dev': [
        'pytest>=6.0.0',
        'pytest-cov>=2.10.0',
        'black>=21.0.0',
        'flake8>=3.8.0',
        'mypy>=0.800',
    ],
    'docs': [
        'sphinx>=3.0.0',
        'sphinx-rtd-theme>=0.5.0',
    ],
    'gui': [
        'tkinter',  # 通常はPythonに含まれているが、一部のLinuxディストリビューションでは別途インストールが必要
    ],
}

# 全ての追加依存関係
EXTRAS_REQUIRE['all'] = list(set(sum(EXTRAS_REQUIRE.values(), [])))

setup(
    # パッケージ基本情報
    name='pypsgemu',
    version='1.0.0',
    description='AY-3-8910 PSG Emulator - Complete software emulation of the AY-3-8910 sound chip',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    
    # 作者・連絡先情報
    author='Siska-Tech',
    author_email='siska-tech@example.com',
    url='https://github.com/siska-tech/pypsgemu',
    
    # ライセンス
    license='MIT',
    
    # 分類
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Emulators',
    ],
    
    # キーワード
    keywords='ay-3-8910 psg emulator sound audio chip retro gaming',
    
    # パッケージ構成
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    python_requires='>=3.8',
    
    # 依存関係
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    
    # パッケージデータ
    package_data={
        'pypsgemu': [
            'data/*.json',
            'data/*.txt',
        ],
    },
    
    # エントリーポイント
    entry_points={
        'console_scripts': [
            'pypsgemu-demo=pypsgemu.cli:demo_main',
            'pypsgemu-debug=pypsgemu.cli:debug_main',
            'pypsgemu-test=pypsgemu.cli:test_main',
        ],
        'gui_scripts': [
            'pypsgemu-gui=pypsgemu.gui:main',
        ],
    },
    
    # プロジェクトURL
    project_urls={
        'Documentation': 'https://github.com/siska-tech/pypsgemu/blob/main/README.md',
        'Source': 'https://github.com/siska-tech/pypsgemu',
        'Tracker': 'https://github.com/siska-tech/pypsgemu/issues',
        'Changelog': 'https://github.com/siska-tech/pypsgemu/blob/main/CHANGELOG.md',
    },
    
    # テスト設定
    test_suite='tests',
    tests_require=[
        'pytest>=6.0.0',
        'pytest-cov>=2.10.0',
    ],
    
    # Zipファイルとして実行可能にするか
    zip_safe=False,
    
    # 開発モード用の設定
    include_package_data=True,
)
