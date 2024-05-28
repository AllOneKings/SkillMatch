from setuptools import setup, find_packages

setup(
    name='custom_env',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'pyresparser==1.0.6',
        'youtube-dl==2021.12.17',
        'yt-dlp==2023.12.30',
    ],
    package_data={
        '': ['pyresparser/*', 'youtube_dl/*', 'yt_dlp/*'],
    },
    include_package_data=True,
)